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
# 1. Happy-path round-trip
# ----------------------------------------------------------------------------- #
def test_roundtrip_two_spin_channels():
    """
    Two spin channels → `[MolecularOrbitals]` → flat arrays → identical content.
    """
    n_ao = 4
    raw = [
        _make_raw_block(
            0,  # alpha
            energies=[-0.8, -0.1],
            coeffs=[[0.8, 0.6, 0.0, 0.0], [0.1, -0.99, 0.0, 0.0]],
        ),
        _make_raw_block(
            1,  # beta
            energies=[-0.5, 0.9],
            coeffs=[[0.75, 0.65, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
        ),
    ]

    # --- convert to sections ---
    mos: list[MolecularOrbitals] = mo_to_sections(raw)
    assert len(mos) == 2
    assert {mo.spin_channel for mo in mos} == {0, 1}

    # each section internally consistent
    for mo in mos:
        assert mo.mo_coefficients.shape == (mo.n_mo, mo.n_ao) == (2, n_ao)
        assert mo.mo_energies.shape == (2,)

    # --- convert back ---
    flat = mo_from_sections(mos)

    # energies are concatenated α then β
    exp_e = np.array([-0.8, -0.1, -0.5, 0.9])
    assert np.allclose(flat['energies'], exp_e)

    # coeffs stacked row-wise in the same order
    exp_c = np.vstack([raw[0]['coeffs'], raw[1]['coeffs']])
    assert np.allclose(flat['coeffs'], exp_c)

    # spin labels preserved
    assert np.array_equal(flat['spin'], np.array([0, 0, 1, 1]))

    # AO dimension carried through
    assert flat['n_ao'] == n_ao


# ----------------------------------------------------------------------------- #
# 2. Error handling – inconsistent AO dimension
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
