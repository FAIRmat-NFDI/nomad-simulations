from collections.abc import Generator

import numpy as np
import pytest
from nomad import files, processing
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.datamodel.data import EntryData
from nomad.metainfo import SubSection
from nomad.utils import create_uuid

from nomad_simulations.schema_packages.properties import (
    ElectronicGreensFunction,
    ElectronicSelfEnergy,
    HoppingMatrix,
    HybridizationFunction,
)
from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)


class MatrixPropertiesTestEntry(EntryData):
    electronic_greens_function = SubSection(sub_section=ElectronicGreensFunction.m_def)
    electronic_self_energy = SubSection(sub_section=ElectronicSelfEnergy.m_def)
    hybridization_function = SubSection(sub_section=HybridizationFunction.m_def)
    hopping_matrix = SubSection(sub_section=HoppingMatrix.m_def)
    molecular_orbitals = SubSection(sub_section=MolecularOrbitals.m_def)


@pytest.fixture(scope='module')
def server_context() -> Generator[ServerContext, None, None]:
    upload_id = f'test_upload_matrix_properties_h5_{create_uuid()}'
    upload_files = files.StagingUploadFiles(upload_id, create=True)
    upload = processing.Upload(upload_id=upload_id)
    try:
        yield ServerContext(upload=upload)
    finally:
        upload_files.delete()


@pytest.fixture
def archive_with_matrix_properties(
    server_context: ServerContext,
) -> tuple[EntryArchive, MatrixPropertiesTestEntry, str, str]:
    upload_id = server_context.upload.upload_id
    entry_id = 'test_entry_matrix_properties_h5'
    data = MatrixPropertiesTestEntry(
        electronic_greens_function=ElectronicGreensFunction(),
        electronic_self_energy=ElectronicSelfEnergy(),
        hybridization_function=HybridizationFunction(),
        hopping_matrix=HoppingMatrix(),
        molecular_orbitals=MolecularOrbitals(),
    )
    archive = EntryArchive(
        m_context=server_context,
        metadata=EntryMetadata(upload_id=upload_id, entry_id=entry_id),
        data=data,
    )
    return archive, data, upload_id, entry_id


def test_complex_matrix_properties_are_stored_in_hdf5(
    archive_with_matrix_properties,
):
    archive, data, upload_id, entry_id = archive_with_matrix_properties
    values = {
        'electronic_greens_function': np.array(
            [[[[1.0 + 2.0j, 3.0 - 4.0j]]]], dtype=np.complex128
        ),
        'electronic_self_energy': np.array(
            [[[[5.0 - 6.0j, 7.0 + 8.0j]]]], dtype=np.complex128
        ),
        'hybridization_function': np.array(
            [[[[9.0 + 10.0j, 11.0 - 12.0j]]]], dtype=np.complex128
        ),
        'hopping_matrix': np.array(
            [[[13.0 + 14.0j, 15.0 - 16.0j]]], dtype=np.complex128
        ),
    }
    mo_coefficients = np.array([[1.0, 0.0], [0.1, 0.9]], dtype=np.float64)
    mo_coefficients_im = np.array([[0.0, 0.0], [0.2, -0.2]], dtype=np.float64)

    for quantity_name, value in values.items():
        getattr(data, quantity_name).value = value
    data.molecular_orbitals.mo_coefficients = mo_coefficients
    data.molecular_orbitals.mo_coefficients_im = mo_coefficients_im

    serialized = archive.m_to_dict()

    for quantity_name, expected in values.items():
        assert (
            serialized['data'][quantity_name]['value']
            == f'/uploads/{upload_id}/archive/{entry_id}#/data/{quantity_name}/value'
        )
        with getattr(data, quantity_name).value as dataset:
            assert dataset.dtype == np.dtype(np.complex128)
            assert dataset.shape == expected.shape
            assert np.array_equal(dataset[()], expected)

    for quantity_name, expected in (
        ('mo_coefficients', mo_coefficients),
        ('mo_coefficients_im', mo_coefficients_im),
    ):
        assert (
            serialized['data']['molecular_orbitals'][quantity_name]
            == f'/uploads/{upload_id}/archive/{entry_id}#/data/molecular_orbitals/{quantity_name}'
        )
        with getattr(data.molecular_orbitals, quantity_name) as dataset:
            assert dataset.dtype == np.dtype(np.float64)
            assert dataset.shape == expected.shape
            assert np.array_equal(dataset[()], expected)
