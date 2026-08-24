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

    # Frontier-orbital resolution: `_normalized` is derived purely from `value` and
    # `occupations` (canonical orbitals with an occupied/unoccupied boundary),
    # independent of the `_parsed` provenance fields, which are never used as a
    # fallback nor overwritten.
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
        # parsed fields are set to values distinct from the derived ones, so the
        # assertions prove `_normalized` ignores them and they survive intact.
        mo = MolecularOrbitals(
            kind=kind,
            value=np.array(value),
            occupations=np.array(occ),
            homo_parsed=-0.9,
            lumo_parsed=0.4,
            homo_lumo_gap_parsed=2.0,
        )
        mo.normalize(archive=EntryArchive(), logger=logger)

        # `_normalized` reflects the derivation (or is unset), never the parsed values
        e_homo, e_lumo, e_gap = expected
        for name, exp in (
            ('homo_normalized', e_homo),
            ('lumo_normalized', e_lumo),
            ('homo_lumo_gap_normalized', e_gap),
        ):
            actual = getattr(mo, name)
            if exp is None:
                assert actual is None
            else:
                assert actual.magnitude == pytest.approx(exp)
        # when derived, the gap is exactly the stored pair, so it stays consistent
        if e_gap is not None:
            assert mo.homo_lumo_gap_normalized.magnitude == pytest.approx(
                (mo.lumo_normalized - mo.homo_normalized).magnitude
            )

        # `_parsed` provenance is untouched regardless of derivation
        assert mo.homo_parsed.magnitude == pytest.approx(-0.9)
        assert mo.lumo_parsed.magnitude == pytest.approx(0.4)
        assert mo.homo_lumo_gap_parsed.magnitude == pytest.approx(2.0)
