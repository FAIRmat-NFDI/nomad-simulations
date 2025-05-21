# nomad_simulations/schema_packages/utils/mo_convert.py
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from nomad.datamodel.data import ArchiveSection

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)


# ----------------------------------------------------------------------------- #
# Public API
# ----------------------------------------------------------------------------- #
def to_sections(data: list[dict[str, Any]]) -> list[MolecularOrbitals]:
    """
    Convert *raw* MO data (already loaded by a parser) → NOMAD sections.

    Each element of *data* is a dict with at minimum:
        spin_channel   - 0 (α) or 1 (β)
        energies       - shape (n_mo,)
        coeffs         - shape (n_mo, n_ao)

    Optional keys:
        occupations    - shape (n_mo,)
        basis_set_ref  - path or section
        mo_type        - 'canonical', 'natural', …

    Returns
    -------
    list[MolecularOrbitals]
    """
    out: list[MolecularOrbitals] = []
    for blk in data:
        mo = MolecularOrbitals(
            spin_channel=int(blk['spin_channel']),
            mo_energies=np.asarray(blk['energies']),
            mo_coefficients=np.asarray(blk['coeffs']),
            mo_occupations=np.asarray(blk.get('occupations', []))
            if blk.get('occupations') is not None
            else None,
            basis_set_ref=blk.get('basis_set_ref'),
            mo_type=blk.get('mo_type', 'canonical'),
        )
        mo.normalize(None, None)  # local consistency check
        out.append(mo)

    return out


def from_sections(mos: Sequence[MolecularOrbitals]) -> dict[str, np.ndarray]:
    """
    Pack a sequence of `MolecularOrbitals` back into plain NumPy arrays.

    Useful for exporting to third-party writers.

    Returns dict with keys:
        'energies', 'coeffs', 'occupations', 'spin'  (all concatenated)
        'n_ao'   – common AO dimension
    """
    energies, coeffs, occ, spin = [], [], [], []

    # sanity: all share the same AO dimension
    n_ao_set = {mo.n_ao for mo in mos}
    if len(n_ao_set) != 1:
        raise ValueError('Inconsistent AO dimensions across spin channels.')
    n_ao = n_ao_set.pop()

    for mo in mos:
        energies.append(mo.mo_energies)
        coeffs.append(mo.mo_coefficients)
        if mo.mo_occupations is not None:
            occ.append(mo.mo_occupations)
        spin.append(np.full(mo.n_mo, mo.spin_channel, dtype=int))

    return dict(
        energies=np.concatenate(energies),
        coeffs=np.vstack(coeffs),
        occupations=np.concatenate(occ) if occ else None,
        spin=np.concatenate(spin),
        n_ao=n_ao,
    )
