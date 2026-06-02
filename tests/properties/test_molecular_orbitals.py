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

    def error(self, message: str, *args, **kwargs) -> None:
        self.errors.append(message % args if args else message)

    def warning(self, *args, **kwargs) -> None:
        pass


@pytest.fixture
def archive_with_mo() -> tuple[EntryArchive, MolecularOrbitals, str, str]:
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
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_mo is None
        assert molecular_orbitals.n_ao is None
        assert any('must be a 2D dataset' in error for error in logger.errors)

    def test_normalize_logs_coefficient_shape_mismatches(self, archive_with_mo):
        _, molecular_orbitals, _, _ = archive_with_mo
        logger = RecordingLogger()

        molecular_orbitals.n_mo = 2
        molecular_orbitals.n_ao = 2
        molecular_orbitals.mo_coefficients = np.ones((3, 4), dtype=np.float64)
        molecular_orbitals.mo_coefficients_im = np.ones((5, 6), dtype=np.float64)
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert any(
            'mo_coefficients` shape must match' in error for error in logger.errors
        )
        assert any(
            'mo_coefficients_im` shape must match' in error for error in logger.errors
        )
        assert any(
            '`mo_coefficients_im` shape must match `mo_coefficients`' in error
            for error in logger.errors
        )
