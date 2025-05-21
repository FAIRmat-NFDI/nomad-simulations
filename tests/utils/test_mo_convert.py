# tests/test_mo_convert.py
"""
Unit–tests for the molecular-orbital conversion helpers in
`nomad_simulations.schema_packages.utils.mo_convert`.
"""

from __future__ import annotations

import numpy as np
import pytest

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)
from nomad_simulations.schema_packages.utils.mo_convert import (
    from_sections as mo_from_sections,
)
from nomad_simulations.schema_packages.utils.mo_convert import (
    to_sections as mo_to_sections,
)


def _make_raw_block(spin: int, energies: list[float], coeffs: list[list[float]]):
    """Return a single *raw* MO block ready for `mo_to_sections`."""
    return dict(
        spin_channel=spin,
        energies=np.asarray(energies),
        coeffs=np.asarray(coeffs),
        occupations=[2.0 if e < 0 else 0.0 for e in energies],
    )


# ----------------------------------------------------------------------------- #
# Error handling – inconsistent AO dimension
# ----------------------------------------------------------------------------- #
def test_from_sections_inconsistent_ao_dim_raises():
    """
    If two MO sections have different AO sizes, `mo_from_sections` must raise.
    """
    mo_good = MolecularOrbitals(
        spin_channel=0,
        mo_energies=np.array([-0.5]),
        mo_coefficients=np.array([[1.0, 0.0]]),  # n_ao = 2
    )
    mo_good.normalize(None, None)

    mo_bad = MolecularOrbitals(
        spin_channel=1,
        mo_energies=np.array([-0.3]),
        mo_coefficients=np.array([[1.0, 0.0, 0.0]]),  # n_ao = 3  (mismatch!)
    )
    mo_bad.normalize(None, None)

    with pytest.raises(ValueError, match='Inconsistent AO dimensions'):
        mo_from_sections([mo_good, mo_bad])
