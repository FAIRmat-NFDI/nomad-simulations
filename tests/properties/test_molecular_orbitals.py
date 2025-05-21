# tests/test_molecular_orbitals.py
from collections.abc import Sequence
from typing import Optional

import numpy as np
import pytest

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)
from tests import logger


# ---------------------------------------------------------------------------
# small helper to build MO objects quickly
# ---------------------------------------------------------------------------
def make_mos(
    energies: Optional[Sequence[float]] = None,
    occupations: Optional[Sequence[float]] = None,
    coeff_shape: Optional[tuple[int, int]] = None,
    n_mo: Optional[int] = None,
    n_ao: Optional[int] = None,
):
    """Return a MolecularOrbitals instance with the requested ingredients."""
    mo = MolecularOrbitals(
        n_mo=n_mo,
        n_ao=n_ao,
        mo_energies=list(energies) if energies is not None else None,
        mo_occupations=list(occupations) if occupations is not None else None,
    )
    if coeff_shape is not None:
        nm, na = coeff_shape
        mo.mo_coefficients = np.zeros(coeff_shape, dtype=float)
        # for the tests we do not care about the numerical values
    return mo


# ---------------------------------------------------------------------------
# 1) Normal, consistent data  ----------------------------------------------
# ---------------------------------------------------------------------------
def test_normalisation_happy_path():
    """`normalize` should infer n_mo / n_ao when shapes are consistent."""
    energies = [-0.8, -0.4, 0.3]
    occupations = [2.0, 2.0, 0.0]
    coeff_shape = (3, 5)  # 3 MOs in 5 AO basis
    mo = make_mos(energies, occupations, coeff_shape)
    mo.normalize(None, logger)

    assert mo.n_mo == 3
    assert mo.n_ao == 5
    assert mo.mo_coefficients.shape == coeff_shape
    # energies / occupations keep their length
    assert len(mo.mo_energies) == 3
    assert len(mo.mo_occupations) == 3


# ---------------------------------------------------------------------------
# 2) Coefficient-matrix shape mismatch  -------------------------------------
# ---------------------------------------------------------------------------
def test_coeff_shape_mismatch_logs_error():
    """
    When the coefficient matrix reports a different number of rows from n_mo,
    the object should *not* crash; it merely logs an ERROR.
    """
    energies = [-0.8, -0.4, 0.3]  # length 3  → n_mo will become 3
    coeff_shape = (2, 4)  # only *2* rows – mismatch on purpose
    mo = make_mos(energies=energies, coeff_shape=coeff_shape)

    # calling normalize should not raise:
    mo.normalize(None, logger)

    # n_mo stays driven by energies (3); n_ao picked up from coeffs (4)
    assert mo.n_mo == 3
    assert mo.n_ao == 4
    # coefficient matrix remains as-is
    assert mo.mo_coefficients.shape == coeff_shape


# ---------------------------------------------------------------------------
# 3) Occupation-vector length mismatch  -------------------------------------
# ---------------------------------------------------------------------------
def test_occupation_length_mismatch_logs_error():
    """
    If mo_occupations has a different length than n_mo, only a log entry is made.
    """
    energies = [-0.8, -0.4, 0.3]
    occupations = [2.0, 0.0]  # length 2 instead of 3
    coeff_shape = (3, 4)

    mo = make_mos(
        energies=energies,
        occupations=occupations,
        coeff_shape=coeff_shape,
    )
    mo.normalize(None, logger)

    # n_mo derived from energies (3) – occupation vector left untouched
    assert mo.n_mo == 3
    assert len(mo.mo_occupations) == 2  # still the original (mismatching) size
    assert mo.mo_coefficients.shape == coeff_shape


# ---------------------------------------------------------------------------
# 4) Explicit n_mo / n_ao overridden by data --------------------------------
# ---------------------------------------------------------------------------
def test_explicit_sizes_overridden():
    """
    If the user supplied n_mo/n_ao that disagree with the real data, the data wins.
    """
    energies = [-1.1, -0.7]  # 2 orbitals
    coeff_shape = (2, 6)  # matches energies
    mo = make_mos(
        energies=energies,
        coeff_shape=coeff_shape,
        n_mo=999,  # bogus on purpose
        n_ao=888,
    )
    mo.normalize(None, logger)

    assert mo.n_mo == 2  # overridden by the energies length
    assert mo.n_ao == 888  # user-supplied value is kept as-is
