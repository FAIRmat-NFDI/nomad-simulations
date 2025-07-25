import numpy as np
import pytest

from nomad_simulations.schema_packages.properties.integrals import (
    OneElectronIntegral,
    TwoElectronIntegral,
)


# -----------------------------------------------------------------------------#
# helpers                                                             #
# -----------------------------------------------------------------------------#
def make_1e(kind: str, dim: int) -> OneElectronIntegral:
    return OneElectronIntegral(
        operator_kind=kind,
        basis_representation='ao',
        component='real',
        n_functions=dim,
        value=np.random.rand(dim, dim),
    )


def make_2e_dense(dim: int) -> TwoElectronIntegral:
    return TwoElectronIntegral(
        basis_representation='ao',
        component='real',
        storage_scheme='dense',
        n_functions=dim,
        eri_dense=np.random.rand(dim, dim, dim, dim),
    )


def make_2e_sparse(dim: int, nelem: int) -> TwoElectronIntegral:
    idx = np.random.randint(low=0, high=dim, size=(nelem, 4))
    val = np.random.rand(nelem)
    return TwoElectronIntegral(
        basis_representation='mo',
        component='imag',
        storage_scheme='sparse',
        n_functions=dim,
        eri_indices=idx,
        eri_values=val,
    )


def make_2e_chol(dim: int, nvec: int) -> TwoElectronIntegral:
    chol = np.random.rand(nvec, dim, dim)
    return TwoElectronIntegral(
        basis_representation='ao',
        component='real',
        storage_scheme='cholesky',
        n_functions=dim,
        eri_cholesky_num=nvec,
        eri_cholesky=chol,
    )


# -----------------------------------------------------------------------------#
# one-electron                                                                 #
# -----------------------------------------------------------------------------#
@pytest.mark.parametrize('dim', [3, 7])
def test_one_electron_shapes(dim):
    oe = make_1e('overlap', dim)
    assert oe.value.shape == (dim, dim)
    assert oe.n_functions == dim


# -----------------------------------------------------------------------------#
# two-electron – dense                                                         #
# -----------------------------------------------------------------------------#
@pytest.mark.parametrize('dim', [2, 5])
def test_two_electron_dense_shapes(dim):
    te = make_2e_dense(dim)
    assert te.eri_dense.shape == (dim, dim, dim, dim)
    assert te.n_functions == dim


# -----------------------------------------------------------------------------#
# two-electron – sparse                                                        #
# -----------------------------------------------------------------------------#
def test_two_electron_sparse_shapes():
    dim, nelem = 4, 10
    te = make_2e_sparse(dim, nelem)
    assert te.eri_indices.shape == (nelem, 4)
    assert te.eri_values.shape == (nelem,)
    assert te.n_functions == dim


# -----------------------------------------------------------------------------#
# two-electron – cholesky                                                      #
# -----------------------------------------------------------------------------#
@pytest.mark.parametrize('dim,nvec', [(3, 5), (2, 8)])
def test_two_electron_cholesky_shapes(dim, nvec):
    te = make_2e_chol(dim, nvec)
    assert te.eri_cholesky.shape == (nvec, dim, dim)
    assert te.eri_cholesky_num == nvec
    assert te.n_functions == dim
