from collections.abc import Generator

import numpy as np
import pytest
from nomad import files, processing
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.datamodel.data import EntryData
from nomad.metainfo import SubSection
from nomad.utils import create_uuid

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)

from . import logger


class MOTestEntry(EntryData):
    molecular_orbitals = SubSection(sub_section=MolecularOrbitals.m_def)


class RecordingLogger:
    def __init__(self):
        self.errors: list[str] = []
        self.error_contexts: list[dict] = []

    def error(self, message: str, *args, **kwargs) -> None:
        self.errors.append(message % args if args else message)
        self.error_contexts.append(kwargs)

    def warning(self, *args, **kwargs) -> None:
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
    archive = EntryArchive(
        m_context=ServerContext(upload=upload),
        metadata=EntryMetadata(upload_id=upload_id, entry_id=entry_id),
        data=MOTestEntry(molecular_orbitals=molecular_orbitals),
    )
    try:
        yield archive, molecular_orbitals, upload_id, entry_id
    finally:
        upload_files.delete()


class TestMolecularOrbitals:
    def test_mo_coefficients_are_stored_in_hdf5(self, archive_with_mo):
        archive, molecular_orbitals, upload_id, entry_id = archive_with_mo
        coeff_real = np.array([[1.0, 0.0], [0.1, 0.9]], dtype=np.float64)
        coeff_imag = np.array([[0.0, 0.0], [0.2, -0.2]], dtype=np.float64)

        molecular_orbitals.mo_coefficients = coeff_real
        molecular_orbitals.mo_coefficients_im = coeff_imag

        serialized = archive.m_to_dict()
        assert (
            serialized['data']['molecular_orbitals']['mo_coefficients']
            == f'/uploads/{upload_id}/archive/{entry_id}#/data/molecular_orbitals/mo_coefficients'
        )
        assert (
            serialized['data']['molecular_orbitals']['mo_coefficients_im']
            == f'/uploads/{upload_id}/archive/{entry_id}#/data/molecular_orbitals/mo_coefficients_im'
        )

        with molecular_orbitals.mo_coefficients as dataset:
            assert dataset.shape == (2, 2)
            assert np.allclose(dataset[()], coeff_real)

        with molecular_orbitals.mo_coefficients_im as dataset:
            assert dataset.shape == (2, 2)
            assert np.allclose(dataset[()], coeff_imag)

    def test_normalize_infers_dimensions_from_hdf5_coefficients(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        coeff_real = np.array(
            [[1.0, 0.0, 0.5], [0.1, 0.9, 0.2], [0.0, 0.4, 0.8]], dtype=np.float64
        )

        molecular_orbitals.mo_coefficients = coeff_real
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_mo == 3
        assert molecular_orbitals.n_ao == 3

    def test_normalize_logs_invalid_coefficient_rank(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        logger = RecordingLogger()

        molecular_orbitals.mo_coefficients = np.ones(3, dtype=np.float64)
        molecular_orbitals.mo_spin = np.zeros(4, dtype=np.int32)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_mo == 4
        assert molecular_orbitals.n_ao is None
        assert 'Molecular orbital coefficients must be a 2D dataset.' in logger.errors
        assert {
            'quantity_name': 'mo_coefficients',
            'shape': (3,),
        } in logger.error_contexts

    def test_normalize_infers_dimensions_from_imaginary_coefficients(
        self, archive_with_mo
    ):
        _, molecular_orbitals, _, _ = archive_with_mo

        molecular_orbitals.mo_coefficients_im = np.ones((3, 4), dtype=np.float64)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_mo == 3
        assert molecular_orbitals.n_ao == 4

    def test_normalize_logs_coefficient_shape_mismatches(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        logger = RecordingLogger()

        molecular_orbitals.n_mo = 2
        molecular_orbitals.n_ao = 2
        molecular_orbitals.mo_coefficients = np.ones((3, 4), dtype=np.float64)
        molecular_orbitals.mo_coefficients_im = np.ones((5, 6), dtype=np.float64)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        shape_mismatch_message = (
            'Molecular orbital coefficient shape does not match expected shape.'
        )
        assert logger.errors.count(shape_mismatch_message) == 2
        assert 'Molecular orbital coefficient shapes do not match.' in logger.errors
        assert {
            'quantity_name': 'mo_coefficients',
            'shape': (3, 4),
            'expected_shape': (2, 2),
        } in logger.error_contexts
        assert {
            'quantity_name': 'mo_coefficients_im',
            'shape': (5, 6),
            'expected_shape': (2, 2),
        } in logger.error_contexts
        assert {
            'mo_coefficients_shape': (3, 4),
            'mo_coefficients_im_shape': (5, 6),
        } in logger.error_contexts
