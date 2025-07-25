from typing import Any, Optional

import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)

from . import logger


def generate_molecular_orbitals(**kwargs: Any) -> MolecularOrbitals:
    """
    `MolecularOrbitals` constructor.
    # TODO EBB
    """
    return MolecularOrbitals(**kwargs)


# -----------------------------------------------------------------------------#
# 1. `n_mo` and `n_ao` inferred from the coefficient matrix                    #
# -----------------------------------------------------------------------------#
def test_infer_from_coefficients():
    coeff = np.random.rand(6, 4)  # (n_mo = 6, n_ao = 4)
    mo = generate_molecular_orbitals(
        mo_coefficients=coeff,
        mo_spin=[0, 1, 0, 1, 0, 1],
    )

    mo.normalize(EntryArchive(), logger)

    assert mo.n_mo == 6
    assert mo.n_ao == 4


# -----------------------------------------------------------------------------#
# 2. `n_mo` inferred from the length of `mo_spin` when no coefficients given    #
# -----------------------------------------------------------------------------#
def test_infer_from_spin_only():
    mo = generate_molecular_orbitals(
        mo_spin=[0, 0, 1, 1, 0],
        mo_energies=[0.0, -0.1, -0.2, -0.3, -0.4],  # matches length
    )

    mo.normalize(EntryArchive(), logger)

    assert mo.n_mo == 5
    assert mo.n_ao is None  # cannot be deduced


# -----------------------------------------------------------------------------#
# 3. `n_mo` inferred from `mo_energies` when it is the only sized array        #
# -----------------------------------------------------------------------------#
def test_infer_from_energies_only():
    energies = np.linspace(-0.5, 0.4, 10)
    mo = generate_molecular_orbitals(
        mo_energies=energies,
        mo_spin=list(range(10)),
    )

    mo.normalize(EntryArchive(), logger)

    assert mo.n_mo == 10
    # n_ao remains None because no coefficient matrix was provided
    assert mo.n_ao is None
