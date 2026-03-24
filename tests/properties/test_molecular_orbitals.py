import numpy as np
from nomad import files, processing
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.datamodel.data import EntryData
from nomad.metainfo import SubSection

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)

from . import logger


class MOTestEntry(EntryData):
    molecular_orbitals = SubSection(sub_section=MolecularOrbitals.m_def)


def create_archive_with_mo() -> tuple[EntryArchive, MolecularOrbitals, str, str]:
    upload_id = 'test_upload_molecular_orbitals_h5'
    entry_id = 'test_entry_molecular_orbitals_h5'
    _ = files.StagingUploadFiles(upload_id, create=True)
    upload = processing.Upload(upload_id=upload_id)
    molecular_orbitals = MolecularOrbitals()
    archive = EntryArchive(
        m_context=ServerContext(upload=upload),
        metadata=EntryMetadata(upload_id=upload_id, entry_id=entry_id),
        data=MOTestEntry(molecular_orbitals=molecular_orbitals),
    )
    return archive, molecular_orbitals, upload_id, entry_id


class TestMolecularOrbitals:
    def test_mo_coefficients_are_stored_in_hdf5(self):
        archive, molecular_orbitals, upload_id, entry_id = create_archive_with_mo()
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

    def test_normalize_infers_dimensions_from_hdf5_coefficients(self):
        _, molecular_orbitals, _, _ = create_archive_with_mo()
        coeff_real = np.array(
            [[1.0, 0.0, 0.5], [0.1, 0.9, 0.2], [0.0, 0.4, 0.8]], dtype=np.float64
        )

        molecular_orbitals.mo_coefficients = coeff_real
        molecular_orbitals.normalize(archive=EntryArchive(), logger=logger)

        assert molecular_orbitals.n_mo == 3
        assert molecular_orbitals.n_ao == 3
