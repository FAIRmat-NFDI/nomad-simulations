from collections.abc import Generator

import numpy as np
import pytest
from nomad import files, processing
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.utils import create_uuid

from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.electronic_eigenvalues import (
    ElectronicEigenvalues,
)
from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    FrontierLevels,
    MOGap,
    MolecularOrbitals,
)

from . import logger


class RecordingLogger:
    def __init__(self):
        self.errors: list[str] = []
        self.error_contexts: list[dict] = []
        self.warnings: list[str] = []
        self.warning_contexts: list[dict] = []

    def error(self, message: str, *args, **kwargs) -> None:
        self.errors.append(message % args if args else message)
        self.error_contexts.append(kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self.warnings.append(message % args if args else message)
        self.warning_contexts.append(kwargs)

    def info(self, *args, **kwargs) -> None:
        pass

    def debug(self, *args, **kwargs) -> None:
        pass


@pytest.fixture
def archive_with_mo() -> Generator[
    tuple[EntryArchive, MolecularOrbitals, str, str], None, None
]:
    upload_id = f'test_upload_molecular_orbitals_h5_{create_uuid()}'
    entry_id = 'test_entry_molecular_orbitals_h5'
    upload_files = files.StagingUploadFiles(upload_id, create=True)
    upload = processing.Upload(upload_id=upload_id)
    molecular_orbitals = MolecularOrbitals()
    outputs = Outputs(molecular_orbitals=[molecular_orbitals])
    simulation = Simulation(outputs=[outputs])
    archive = EntryArchive(
        m_context=ServerContext(upload=upload),
        metadata=EntryMetadata(upload_id=upload_id, entry_id=entry_id),
        data=simulation,
    )
    try:
        yield archive, molecular_orbitals, upload_id, entry_id
    finally:
        upload_files.delete()


class TestMolecularOrbitals:
    def test_is_independent_physical_property(self):
        molecular_orbitals = MolecularOrbitals()

        assert issubclass(MolecularOrbitals, PhysicalProperty)
        assert isinstance(molecular_orbitals, PhysicalProperty)
        assert not isinstance(molecular_orbitals, ElectronicEigenvalues)

    def test_stored_in_outputs(self):
        """MolecularOrbitals can be stored through the canonical Outputs path."""
        mo = MolecularOrbitals()
        outputs = Outputs(molecular_orbitals=[mo])
        simulation = Simulation(outputs=[outputs])
        assert simulation.outputs[0].molecular_orbitals[0] is mo

    def test_normalize_infers_dimensions_from_coefficients(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        coeff_real = np.array(
            [[1.0, 0.0, 0.5], [0.1, 0.9, 0.2], [0.0, 0.4, 0.8]], dtype=np.float64
        )
        molecular_orbitals.coefficients = coeff_real
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_mo == 3
        assert molecular_orbitals.n_ao == 3
        with pytest.raises(ValueError):
            molecular_orbitals.n_mo = 0
        with pytest.raises(ValueError):
            molecular_orbitals.n_ao = 0

    def test_normalize_logs_invalid_coefficient_rank(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        rec = RecordingLogger()

        molecular_orbitals.coefficients = np.ones(3, dtype=np.float64)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=rec)

        assert molecular_orbitals.n_mo is None
        assert molecular_orbitals.n_ao is None
        assert (
            'The coefficient matrix must be a 2D dataset with shape [`n_mo`, `n_ao`].'
            in rec.errors
        )

    def test_normalize_infers_dimensions_from_imaginary_coefficients(
        self, archive_with_mo
    ):
        _, molecular_orbitals, _, _ = archive_with_mo

        molecular_orbitals.coefficients_im = np.ones((3, 4), dtype=np.float64)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_mo == 3
        assert molecular_orbitals.n_ao == 4

    @pytest.mark.parametrize(
        'quantity_name, values',
        [
            ('value', np.array([-1.0, -0.5, 0.2])),
            ('occupations', np.array([2.0, 2.0, 0.0, 0.0])),
        ],
    )
    def test_normalize_infers_n_mo_from_orbital_values(
        self, archive_with_mo, quantity_name, values
    ):
        _, molecular_orbitals, _, _ = archive_with_mo
        setattr(molecular_orbitals, quantity_name, values)

        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_mo == len(values)

    def test_normalize_logs_coefficient_shape_mismatches(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        rec = RecordingLogger()

        molecular_orbitals.n_mo = 2
        molecular_orbitals.n_ao = 2
        molecular_orbitals.coefficients = np.ones((3, 4), dtype=np.float64)
        molecular_orbitals.coefficients_im = np.ones((5, 6), dtype=np.float64)
        molecular_orbitals.value = np.array([-1.0, 0.5, 1.0])
        molecular_orbitals.normalize(archive=EntryArchive(), logger=rec)

        assert (
            rec.errors.count(
                'Coefficient matrix shape does not match [`n_mo`, `n_ao`]; check that `n_mo` and `n_ao` are consistent with the dataset dimensions.'
            )
            == 2
        )
        assert (
            'The real and imaginary coefficient matrices have different shapes and cannot be combined.'
            in rec.errors
        )
        assert (
            'Length of a per-orbital quantity does not match `n_mo`; all of `value`, `occupations`, `role`, and `symmetry` must have exactly `n_mo` entries.'
            in rec.errors
        )

    def test_spin_channel_convention(self):
        """Two MolecularOrbitals sections with spin_channel 0 and 1 store independently."""
        mo_alpha = MolecularOrbitals(spin_channel=0)
        mo_beta = MolecularOrbitals(spin_channel=1)
        outputs = Outputs(molecular_orbitals=[mo_alpha, mo_beta])

        assert outputs.molecular_orbitals[0].spin_channel == 0
        assert outputs.molecular_orbitals[1].spin_channel == 1

    def test_does_not_derive_eigenvalue_properties(self):
        molecular_orbitals = MolecularOrbitals(
            value=np.array([-1.0, 0.5]),
            occupations=np.array([2.0, 0.0]),
        )

        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        for quantity_name in ('highest_occupied', 'lowest_unoccupied', 'band_gap'):
            assert quantity_name not in molecular_orbitals.m_def.all_quantities

    # T4: value (orbital energies) unit
    def test_value_unit_is_joule(self):
        assert str(MolecularOrbitals.value.unit) == 'joule'

    # Occupation bounds are enforced by the `occupations` interval datatype, so they
    # are covered where the datatype lives rather than here.
    # NOTE(#468): the spin-resolved maximum (1 for spin orbitals) and a soft-log
    # failure mode are deferred, so a spin-orbital occupation between 1 and 2 is
    # currently accepted rather than flagged.

    # T1 normalize: spin_channel validation
    def test_spin_channel_invalid_value_errors(self):
        rec = RecordingLogger()
        mo = MolecularOrbitals(spin_channel=2)
        mo.normalize(archive=EntryArchive(), logger=rec)

        assert '`spin_channel` must be 0 (alpha) or 1 (beta) when set.' in rec.errors

    # T3: energies optional — natural orbitals without energies normalize cleanly
    def test_natural_orbitals_without_energies_normalize(self, archive_with_mo):
        _, mo, _, _ = archive_with_mo
        rec = RecordingLogger()

        mo.kind = 'natural'
        mo.occupations = np.array([1.0, 0.5, 0.0])
        mo.coefficients = np.ones((3, 4), dtype=np.float64)
        # value (energies) intentionally absent

        mo.normalize(archive=EntryArchive(), logger=rec)

        assert not rec.errors
        assert mo.n_mo == 3
        assert mo.n_ao == 4

    # Frontier resolution: normalization resolves the HOMO/LUMO pair from `value` and
    # `occupations` (canonical orbitals with an occupied/unoccupied boundary), stores it
    # as a resolved `FrontierLevels` (is_derived=True) on the MO, and emits a derived
    # `MOGap` into `Outputs.molecular_orbital_gaps` referencing that pair.
    @pytest.mark.parametrize(
        'kind, value, occ, expected',
        [
            # canonical with a boundary: HOMO/LUMO/gap derived
            (
                'canonical',
                [-2.0, -1.0, 0.5, 1.5],
                [2.0, 2.0, 0.0, 0.0],
                (-1.0, 0.5, 1.5),
            ),
            # unset kind is not assumed canonical
            (None, [-2.0, -1.0, 0.5, 1.5], [2.0, 2.0, 0.0, 0.0], (None, None, None)),
            # explicitly non-canonical
            (
                'natural',
                [-2.0, -1.0, 0.5, 1.5],
                [2.0, 2.0, 0.0, 0.0],
                (None, None, None),
            ),
            # canonical but no occupied/unoccupied boundary
            ('canonical', [-2.0, -1.0], [2.0, 2.0], (None, None, None)),
        ],
    )
    def test_frontier_derivation(self, kind, value, occ, expected):
        outputs = Outputs()
        mo = MolecularOrbitals(
            kind=kind,
            value=np.array(value),
            occupations=np.array(occ),
        )
        outputs.molecular_orbitals.append(mo)
        mo.normalize(archive=EntryArchive(), logger=logger)

        e_homo, e_lumo, e_gap = expected
        resolved = [f for f in mo.frontier_levels if f.is_derived]
        derived_gaps = [g for g in outputs.molecular_orbital_gaps if g.is_derived]

        if e_gap is None:
            # no boundary resolved: no resolved pair, no derived gap
            assert not resolved
            assert not derived_gaps
            return

        # exactly one resolved pair mirroring the derivation
        assert len(resolved) == 1
        pair = resolved[0]
        assert pair.homo.magnitude == pytest.approx(e_homo)
        assert pair.lumo.magnitude == pytest.approx(e_lumo)

        # exactly one derived gap, referencing that pair, value = lumo - homo
        assert len(derived_gaps) == 1
        gap = derived_gaps[0]
        assert gap.value.magnitude == pytest.approx(e_gap)
        assert gap.derived_from is pair
        assert gap.derived_from.is_derived is True

    def test_parsed_normalized_gap(self):
        # A parser-provided (code-reported) frontier pair yields a parsed-normalized
        # gap: is_derived=True, but its source pair is is_derived=False.
        outputs = Outputs()
        mo = MolecularOrbitals(kind='natural')  # no resolvable frontier of its own
        mo.frontier_levels.append(FrontierLevels(homo=-0.9, lumo=0.4, is_derived=False))
        outputs.molecular_orbitals.append(mo)
        mo.normalize(archive=EntryArchive(), logger=logger)

        gaps = outputs.molecular_orbital_gaps
        assert len(gaps) == 1
        gap = gaps[0]
        assert gap.value.magnitude == pytest.approx(1.3)
        assert gap.is_derived is True
        assert gap.derived_from.is_derived is False

    def test_three_gaps_coexist(self):
        # parsed (code-reported), normalized (from resolved frontier), and
        # parsed-normalized (from the parsed frontier) gaps all coexist and are
        # distinguishable via is_derived + derived_from(.is_derived).
        outputs = Outputs()
        mo = MolecularOrbitals(
            kind='canonical',
            value=np.array([-2.0, -1.0, 0.5, 1.5]),
            occupations=np.array([2.0, 2.0, 0.0, 0.0]),
        )
        mo.frontier_levels.append(FrontierLevels(homo=-0.9, lumo=0.4, is_derived=False))
        outputs.molecular_orbitals.append(mo)
        # a code-reported gap, as the parser would emit it (no derivation source)
        outputs.molecular_orbital_gaps.append(MOGap(value=1.1))

        mo.normalize(archive=EntryArchive(), logger=logger)

        gaps = outputs.molecular_orbital_gaps
        assert len(gaps) == 3

        parsed = [g for g in gaps if g.derived_from is None]
        from_resolved = [
            g for g in gaps if g.derived_from is not None and g.derived_from.is_derived
        ]
        from_parsed = [
            g
            for g in gaps
            if g.derived_from is not None and not g.derived_from.is_derived
        ]
        assert len(parsed) == 1 and not parsed[0].is_derived
        assert len(from_resolved) == 1 and from_resolved[0].is_derived
        assert len(from_parsed) == 1 and from_parsed[0].is_derived
        assert from_resolved[0].value.magnitude == pytest.approx(1.5)
        assert from_parsed[0].value.magnitude == pytest.approx(1.3)

    def test_crossed_frontier_gap_clamped_to_zero(self):
        outputs = Outputs()
        mo = MolecularOrbitals(kind='natural')
        mo.frontier_levels.append(FrontierLevels(homo=2.0, lumo=1.0, is_derived=False))
        outputs.molecular_orbitals.append(mo)
        mo.normalize(archive=EntryArchive(), logger=logger)

        assert outputs.molecular_orbital_gaps[0].value.magnitude == pytest.approx(0.0)

    def test_normalize_is_idempotent(self):
        outputs = Outputs()
        mo = MolecularOrbitals(
            kind='canonical',
            value=np.array([-2.0, -1.0, 0.5, 1.5]),
            occupations=np.array([2.0, 2.0, 0.0, 0.0]),
        )
        mo.frontier_levels.append(FrontierLevels(homo=-0.9, lumo=0.4, is_derived=False))
        outputs.molecular_orbitals.append(mo)

        mo.normalize(archive=EntryArchive(), logger=logger)
        n_frontier = len(mo.frontier_levels)
        n_gaps = len(outputs.molecular_orbital_gaps)

        mo.normalize(archive=EntryArchive(), logger=logger)
        assert len(mo.frontier_levels) == n_frontier
        assert len(outputs.molecular_orbital_gaps) == n_gaps

    def test_gaps_not_duplicated_across_reload(self):
        # reprocessing (serialize -> reload -> normalize) must not re-emit gaps: the
        # `_emit_gap` dedup keys on `m_path`, not object identity, so a reloaded
        # `derived_from` (a fresh object) still matches the existing gap.
        def build():
            mo = MolecularOrbitals(
                kind='canonical',
                spin_channel=0,
                value=np.array([-2.0, -1.0, 0.5, 1.5]),
                occupations=np.array([2.0, 2.0, 0.0, 0.0]),
            )
            mo.frontier_levels.append(
                FrontierLevels(homo=-0.9, lumo=0.4, is_derived=False)
            )
            outputs = Outputs(molecular_orbitals=[mo])
            return EntryArchive(data=Simulation(outputs=[outputs]))

        archive = build()
        mo = archive.data.outputs[0].molecular_orbitals[0]
        mo.normalize(archive=archive, logger=logger)
        n_gaps = len(archive.data.outputs[0].molecular_orbital_gaps)
        assert n_gaps == 2  # normalized (from resolved) + parsed-normalized

        reloaded = EntryArchive.m_from_dict(archive.m_to_dict())
        mo2 = reloaded.data.outputs[0].molecular_orbitals[0]
        mo2.normalize(archive=reloaded, logger=logger)
        assert len(reloaded.data.outputs[0].molecular_orbital_gaps) == n_gaps

    def test_spin_channel_propagates_to_gap(self):
        outputs = Outputs()
        mo = MolecularOrbitals(
            kind='canonical',
            spin_channel=1,
            value=np.array([-2.0, -1.0, 0.5, 1.5]),
            occupations=np.array([2.0, 2.0, 0.0, 0.0]),
        )
        outputs.molecular_orbitals.append(mo)
        mo.normalize(archive=EntryArchive(), logger=logger)
        assert outputs.molecular_orbital_gaps[0].spin_channel == 1

    def test_mogap_is_derived_set_from_reference_on_normalize(self):
        # a derived gap that skips `_emit_gap` still resolves is_derived from
        # `derived_from` when its own normalize runs (the `_is_derived` override)
        pair = FrontierLevels(homo=-0.9, lumo=0.4, is_derived=True)
        gap = MOGap(value=1.3, derived_from=pair)
        assert gap.is_derived is False  # stored default before normalize
        gap.normalize(archive=EntryArchive(), logger=logger)
        assert gap.is_derived is True
        # a code-reported gap (no derived_from) stays not-derived
        parsed = MOGap(value=1.1)
        parsed.normalize(archive=EntryArchive(), logger=logger)
        assert parsed.is_derived is False
