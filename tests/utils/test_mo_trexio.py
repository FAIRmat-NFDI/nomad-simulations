import h5py
import numpy as np
import pytest

from nomad_simulations.utils import trexio_to_molecular_orbitals


@pytest.fixture
def trexio_file(tmp_path):
    coeff = np.array([[1.0, 0.0], [0.0, 1.0]])
    energies = np.array([-0.5, 0.8])
    occupations = np.array([2.0, 0.0])

    path = tmp_path / 'dummy.trexio'
    with h5py.File(path, 'w') as f:
        mo = f.create_group('mo')
        mo.create_dataset('mo_num', data=coeff.shape[0])
        mo.create_dataset('mo_coefficient', data=coeff)
        mo.create_dataset('mo_energy', data=energies)
        mo.create_dataset('mo_occupation', data=occupations)
    return path, coeff, energies, occupations


def test_trexio_to_molecular_orbitals(trexio_file):
    path, coeff, energies, occupations = trexio_file
    mo = trexio_to_molecular_orbitals(path, basis_set_ref='basis')

    assert mo.n_mo == 2
    assert mo.n_ao == 2
    np.testing.assert_allclose(mo.mo_coefficients, coeff)
    np.testing.assert_allclose(mo.mo_energies, energies)
    np.testing.assert_allclose(mo.mo_occupations, occupations)
    assert mo.basis_set_ref is not None
