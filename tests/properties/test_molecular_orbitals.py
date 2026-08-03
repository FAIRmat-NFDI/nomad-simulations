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
            ('energies', np.array([-1.0, -0.5, 0.2])),
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
        molecular_orbitals.energies = np.array([-1.0, 0.5, 1.0])
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
            'Length of a per-orbital quantity does not match `n_mo`; all of `energies`, `occupations`, `role`, and `symmetry` must have exactly `n_mo` entries.'
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
            energies=np.array([-1.0, 0.5]),
            occupations=np.array([2.0, 0.0]),
        )

        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        for quantity_name in ('highest_occupied', 'lowest_unoccupied', 'band_gap'):
            assert quantity_name not in molecular_orbitals.m_def.all_quantities

    # T4: energies unit
    def test_energies_unit_is_joule(self):
        assert str(MolecularOrbitals.energies.unit) == 'joule'

    # T1 normalize: occupation validation — spatial (spin-summed) orbitals
    def test_spatial_occupations_pass(self):
        rec = RecordingLogger()
        mo = MolecularOrbitals(occupations=np.array([2.0, 2.0, 0.0, 0.0]))
        mo.normalize(archive=EntryArchive(), logger=rec)

        assert not rec.errors

    def test_spatial_occupation_exceeds_two_errors(self):
        rec = RecordingLogger()
        mo = MolecularOrbitals(occupations=np.array([2.5, 1.0]))
        mo.normalize(archive=EntryArchive(), logger=rec)

        assert any(
            '`occupations` exceed the maximum allowed value' in e for e in rec.errors
        )

    # T1 normalize: occupation validation — spin orbitals
    def test_spin_channel_occupations_pass(self):
        rec = RecordingLogger()
        mo = MolecularOrbitals(spin_channel=0, occupations=np.array([1.0, 1.0, 0.0]))
        mo.normalize(archive=EntryArchive(), logger=rec)

        assert not any('occupations exceed' in e for e in rec.errors)

    def test_spin_channel_occupation_exceeds_one_errors(self):
        rec = RecordingLogger()
        mo = MolecularOrbitals(spin_channel=0, occupations=np.array([1.5, 0.0]))
        mo.normalize(archive=EntryArchive(), logger=rec)

        assert any(
            '`occupations` exceed the maximum allowed value' in e for e in rec.errors
        )

    def test_negative_occupation_errors(self):
        rec = RecordingLogger()
        mo = MolecularOrbitals(occupations=np.array([-0.5, 1.0]))
        mo.normalize(archive=EntryArchive(), logger=rec)

        assert (
            'Occupations must be non-negative, but negative values were found.'
            in rec.errors
        )

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
        # energies intentionally absent

        mo.normalize(archive=EntryArchive(), logger=rec)

        assert not rec.errors
        assert mo.n_mo == 3
        assert mo.n_ao == 4
