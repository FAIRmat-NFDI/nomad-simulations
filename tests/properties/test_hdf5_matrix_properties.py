"""
Tests for matrix quantities migrated to HDF5Dataset:
  ElectronicGreensFunction.value, ElectronicSelfEnergy.value,
  HybridizationFunction.value, HoppingMatrix.value.

Key behavioral notes (documented here, not enforced by infrastructure):
- HDF5Dataset accepts any numpy array without dtype enforcement.  If you
  pass complex64 instead of complex128 it will be stored as complex64.
- Empty arrays (zero-size leading dimension) are stored and read back
  correctly.
"""

import numpy as np
import pytest
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.datamodel.data import EntryData
from nomad.metainfo import SubSection

from nomad_simulations.schema_packages.properties import (
    ElectronicGreensFunction,
    ElectronicSelfEnergy,
    HoppingMatrix,
    HybridizationFunction,
)
from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)

from ..conftest import assert_hdf5_dataset_matches


class MatrixPropertiesTestEntry(EntryData):
    electronic_greens_function = SubSection(sub_section=ElectronicGreensFunction.m_def)
    electronic_self_energy = SubSection(sub_section=ElectronicSelfEnergy.m_def)
    hybridization_function = SubSection(sub_section=HybridizationFunction.m_def)
    hopping_matrix = SubSection(sub_section=HoppingMatrix.m_def)
    molecular_orbitals = SubSection(sub_section=MolecularOrbitals.m_def)


# ---------------------------------------------------------------------------
# Helper that builds a fresh archive for each test to avoid HDF5 path clashes
# ---------------------------------------------------------------------------


def _make_archive(
    server_context: ServerContext,
    entry_id: str,
) -> tuple[EntryArchive, MatrixPropertiesTestEntry]:
    upload_id = server_context.upload.upload_id
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
    return archive, data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMatrixHDF5Storage:
    """Happy-path and edge-case tests for HDF5-backed matrix quantities."""

    def test_valid_complex128_arrays_stored_and_read_back(
        self, hdf5_server_context: ServerContext
    ):
        """Valid complex128 arrays are stored and round-trip through HDF5."""
        archive, data = _make_archive(hdf5_server_context, 'entry_valid_complex128')
        upload_id = hdf5_server_context.upload.upload_id

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
        entry_id = archive.metadata.entry_id

        for quantity_name, expected in values.items():
            assert (
                serialized['data'][quantity_name]['value']
                == f'/uploads/{upload_id}/archive/{entry_id}#/data/{quantity_name}/value'
            )
            assert_hdf5_dataset_matches(
                getattr(data, quantity_name).value,
                expected,
                dtype=np.complex128,
            )

        for mo_name, mo_expected in (
            ('mo_coefficients', mo_coefficients),
            ('mo_coefficients_im', mo_coefficients_im),
        ):
            assert (
                serialized['data']['molecular_orbitals'][mo_name]
                == f'/uploads/{upload_id}/archive/{entry_id}#/data/molecular_orbitals/{mo_name}'
            )
            assert_hdf5_dataset_matches(
                getattr(data.molecular_orbitals, mo_name),
                mo_expected,
                dtype=np.float64,
            )

    def test_empty_complex_array_stored_and_read_back(
        self, hdf5_server_context: ServerContext
    ):
        """An empty leading dimension is stored and read back with the correct shape."""
        archive, data = _make_archive(hdf5_server_context, 'entry_empty_array')

        # shape (0, 2, 2, 2): zero k-points, but well-formed orbital dimensions
        empty_gf = np.zeros((0, 2, 2, 2), dtype=np.complex128)
        data.electronic_greens_function.value = empty_gf
        archive.m_to_dict()

        assert_hdf5_dataset_matches(
            data.electronic_greens_function.value,
            empty_gf,
            dtype=np.complex128,
        )

    def test_dtype_passthrough_not_enforced(self, hdf5_server_context: ServerContext):
        """
        HDF5Dataset does not enforce dtype at the schema level.

        Since the quantity type changed from Quantity(type=np.complex128) to
        Quantity(type=HDF5Dataset), dtype validation no longer happens
        automatically.  Whatever dtype the caller provides is stored as-is.
        This test documents the current behavior: a complex64 array is accepted
        and stored with dtype complex64, not upcasted to complex128.
        """
        archive, data = _make_archive(hdf5_server_context, 'entry_dtype_passthrough')

        arr_c64 = np.array([[[[1.0 + 2.0j]]]], dtype=np.complex64)
        data.electronic_greens_function.value = arr_c64
        archive.m_to_dict()

        # No dtype constraint passed — just verify shape and values round-trip
        assert_hdf5_dataset_matches(
            data.electronic_greens_function.value,
            arr_c64,
        )
        # Document explicitly that the stored dtype is the caller's dtype
        with data.electronic_greens_function.value as ds:
            assert ds.dtype == np.dtype(np.complex64), (
                'HDF5Dataset stores the array with the caller-supplied dtype; '
                'no automatic upcasting to complex128 occurs.'
            )

    def test_hopping_matrix_expected_shape(self, hdf5_server_context: ServerContext):
        """HoppingMatrix.value stores [n_wigner_seitz_points, n_orbitals, n_orbitals]."""
        archive, data = _make_archive(hdf5_server_context, 'entry_hopping_shape')

        n_r, n_orb = 3, 2
        hopping = np.arange(n_r * n_orb * n_orb, dtype=np.complex128).reshape(
            n_r, n_orb, n_orb
        )
        data.hopping_matrix.value = hopping
        archive.m_to_dict()

        assert_hdf5_dataset_matches(
            data.hopping_matrix.value,
            hopping,
            dtype=np.complex128,
        )

    def test_greens_function_expected_shape(self, hdf5_server_context: ServerContext):
        """ElectronicGreensFunction.value stores [n_kpoints, n_freq, n_orb, n_orb]."""
        archive, data = _make_archive(hdf5_server_context, 'entry_gf_shape')

        n_k, n_f, n_o = 2, 4, 3
        gf = (
            np.arange(n_k * n_f * n_o * n_o, dtype=np.float64).reshape(
                n_k, n_f, n_o, n_o
            )
            + 1j * np.ones((n_k, n_f, n_o, n_o))
        ).astype(np.complex128)
        data.electronic_greens_function.value = gf
        archive.m_to_dict()

        assert_hdf5_dataset_matches(
            data.electronic_greens_function.value,
            gf,
            dtype=np.complex128,
        )
