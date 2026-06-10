from collections.abc import Generator

import numpy as np
import pytest
from nomad import files, processing
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.utils import create_uuid

from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)

from . import logger


class RecordingLogger:
    def __init__(self):
        self.errors: list[str] = []
        self.error_contexts: list[dict] = []

    def error(self, message: str, *args, **kwargs) -> None:
        self.errors.append(message % args if args else message)
        self.error_contexts.append(kwargs)

    def warning(self, *args, **kwargs) -> None:
        pass

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

        assert molecular_orbitals.n_levels == 3
        assert molecular_orbitals.n_ao == 3

    def test_normalize_logs_invalid_coefficient_rank(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        rec = RecordingLogger()

        molecular_orbitals.coefficients = np.ones(3, dtype=np.float64)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=rec)

        assert molecular_orbitals.n_levels is None
        assert molecular_orbitals.n_ao is None
        assert 'Molecular orbital coefficients must be a 2D dataset.' in rec.errors
        assert {
            'quantity_name': 'coefficients',
            'shape': (3,),
        } in rec.error_contexts

    def test_normalize_infers_dimensions_from_imaginary_coefficients(
        self, archive_with_mo
    ):
        _, molecular_orbitals, _, _ = archive_with_mo

        molecular_orbitals.coefficients_im = np.ones((3, 4), dtype=np.float64)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_levels == 3
        assert molecular_orbitals.n_ao == 4

    def test_normalize_logs_coefficient_shape_mismatches(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        rec = RecordingLogger()

        molecular_orbitals.n_levels = 2
        molecular_orbitals.n_ao = 2
        molecular_orbitals.coefficients = np.ones((3, 4), dtype=np.float64)
        molecular_orbitals.coefficients_im = np.ones((5, 6), dtype=np.float64)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=rec)

        shape_mismatch_message = (
            'Molecular orbital coefficient shape does not match expected shape.'
        )
        assert rec.errors.count(shape_mismatch_message) == 2
        assert 'Molecular orbital coefficient shapes do not match.' in rec.errors
        assert {
            'quantity_name': 'coefficients',
            'shape': (3, 4),
            'expected_shape': (2, 2),
        } in rec.error_contexts
        assert {
            'quantity_name': 'coefficients_im',
            'shape': (5, 6),
            'expected_shape': (2, 2),
        } in rec.error_contexts
        assert {
            'coefficients_shape': (3, 4),
            'coefficients_im_shape': (5, 6),
        } in rec.error_contexts

    def test_spin_channel_convention(self):
        """Two MolecularOrbitals sections with spin_channel 0 and 1 store independently."""
        mo_alpha = MolecularOrbitals(spin_channel=0)
        mo_beta = MolecularOrbitals(spin_channel=1)
        outputs = Outputs(molecular_orbitals=[mo_alpha, mo_beta])

        assert outputs.molecular_orbitals[0].spin_channel == 0
        assert outputs.molecular_orbitals[1].spin_channel == 1
