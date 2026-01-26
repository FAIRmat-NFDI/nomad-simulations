"""
Helpers to load molecular-orbital data from TREXIO files stored in HDF5.

TREXIO files are HDF5 containers with a `/mo` group holding datasets like
`mo_num`, `mo_coefficient`, `mo_energy`, and `mo_occupation`. We read these
directly with `h5py` so no `trexio` Python package is required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import numpy as np
from nomad.utils import get_logger

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)

logger = get_logger(__name__)


def trexio_to_molecular_orbitals(
    trexio_path: str | Path,
    *,
    basis_set_ref: Any = None,
) -> MolecularOrbitals:
    """
    Load MOs from a TREXIO HDF5 file and return a populated MolecularOrbitals section.

    Only a subset of TREXIO MO metadata is mapped (energies, occupations,
    coefficients, counts). Extend if you need additional fields.
    """

    trexio_path = Path(trexio_path)
    _logged_missing = set()

    with h5py.File(trexio_path, 'r') as handle:
        mo_group = handle.get('mo') or handle.get('/mo')
        if mo_group is None:
            logger.error(
                'trexio_to_molecular_orbitals.missing_mo_group', file=str(trexio_path)
            )
            return MolecularOrbitals()

        mo_num = _read_first(
            mo_group, ['mo_num', 'num'], required=False, logged=_logged_missing
        )
        coeff = _read_first(
            mo_group,
            ['mo_coefficient', 'coefficient'],
            required=True,
            logged=_logged_missing,
        )
        energies = _read_first(
            mo_group, ['mo_energy', 'energy'], required=False, logged=_logged_missing
        )
        occupations = _read_first(
            mo_group,
            ['mo_occupation', 'occupation'],
            required=False,
            logged=_logged_missing,
        )

    mo = MolecularOrbitals()
    if mo_num is not None:
        mo.n_mo = int(np.array(mo_num).item())
    if coeff is not None:
        mo.mo_coefficients = np.asarray(coeff, dtype=np.float64)
        if mo.n_mo is None:
            mo.n_mo = mo.mo_coefficients.shape[0]
        mo.n_ao = mo.mo_coefficients.shape[1]
    if energies is not None:
        mo.mo_energies = np.asarray(energies, dtype=np.float64)
    if occupations is not None:
        mo.mo_occupations = np.asarray(occupations, dtype=np.float64)

    mo.basis_set_ref = basis_set_ref
    return mo


def _read_first(group: h5py.Group, names: list[str], required: bool, logged: set[str]):
    """
    Return the first available dataset among `names` inside the provided group.
    """
    for name in names:
        if name in group:
            data = group[name][()]
            return data
    if required:
        key = '|'.join(names)
        if key not in logged:
            logger.error(
                'trexio_to_molecular_orbitals.missing_required_dataset',
                missing=names,
            )
            logged.add(key)
    return None