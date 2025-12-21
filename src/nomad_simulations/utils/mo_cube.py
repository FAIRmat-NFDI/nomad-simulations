"""
Helpers to load molecular-orbital Gaussian cube files.

The parsing uses ASE (already a transitive dependency via `nomad-lab`) to
obtain the volumetric data and atom metadata. We additionally parse the cube
header to expose grid origin and voxel vectors so the data can be written into
NOMAD archives (e.g., HDF5 datasets referenced from the GUI).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from ase.io.cube import read_cube_data

from nomad_simulations.schema_packages.properties.molecular_orbitals import (
    MolecularOrbitals,
)


def _parse_cube_grid(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Parse the cube header to obtain origin and voxel vectors.

    Returns
    -------
    origin : np.ndarray, shape (3,)
        Origin of the grid in Bohr (cube files are specified in Bohr).
    voxel_vectors : np.ndarray, shape (3, 3)
        Voxel vectors (a_x, b_y, c_z) in Bohr.
    shape : np.ndarray, shape (3,)
        Grid dimensions (n_x, n_y, n_z).
    """

    with path.open('r', encoding='utf-8') as handle:
        # Skip the two comment lines
        _ = handle.readline()
        _ = handle.readline()

        # Line 3: number of atoms (signed) and origin
        parts = handle.readline().split()
        if len(parts) < 4:
            raise ValueError(f'Cube header malformed in {path}')
        origin = np.array(list(map(float, parts[1:4])), dtype=np.float64)

        shape = []
        voxel_vectors = []
        for _ in range(3):
            parts = handle.readline().split()
            if len(parts) < 4:
                raise ValueError(f'Cube header missing grid vectors in {path}')
            shape.append(int(parts[0]))
            voxel_vectors.append([float(parts[1]), float(parts[2]), float(parts[3])])

    return (
        origin,
        np.array(voxel_vectors, dtype=np.float64),
        np.array(shape, dtype=np.int32),
    )


def cube_to_molecular_orbitals(
    cube_path: str | Path,
    *,
    mo_index: int | None = None,
    spin: int = 0,
    energy_ev: float | None = None,
    occupation: float | None = None,
    basis_set_ref=None,
) -> tuple[MolecularOrbitals, dict]:
    """
    Load a Gaussian cube file that contains a *single* MO amplitude grid and
    convert it to a MolecularOrbitals container plus grid metadata.

    Parameters
    ----------
    cube_path
        Path to the cube file to read. The file is assumed to store a single
        MO amplitude (typical Gaussian-style MO cubes).
    mo_index
        Optional MO index label to store alongside the grid. When omitted, the
        index is left unset.
    spin
        Spin channel of the orbital (0: alpha, 1: beta).
    energy_ev
        Optional orbital energy in electron_volt.
    occupation
        Optional occupation number for this orbital.
    basis_set_ref
        Optional reference to an `AtomCenteredBasisSet` instance if you have
        the AO basis available elsewhere in the archive.

    Returns
    -------
    molecular_orbitals : MolecularOrbitals
        A minimal MolecularOrbitals section with one MO and the provided
        metadata populated.
    grid : dict
        A small dict with the volumetric grid ready to write into an HDF5
        dataset (e.g., under `results/volumes/mo_{idx}`). Keys:
          - values (np.ndarray, shape (n_x, n_y, n_z)): MO amplitude
          - origin (np.ndarray, shape (3,)): grid origin (Bohr)
          - voxel_vectors (np.ndarray, shape (3, 3)): voxel vectors (Bohr)
          - shape (np.ndarray, shape (3,)): grid dimensions
    """

    cube_path = Path(cube_path)
    values, atoms = read_cube_data(str(cube_path))
    origin, voxel_vectors, shape = _parse_cube_grid(cube_path)

    mo = MolecularOrbitals()
    mo.n_mo = 1
    mo.mo_spin = np.array([spin], dtype=np.int32)
    mo.mo_energies = (
        None if energy_ev is None else np.array([energy_ev], dtype=np.float64)
    )
    mo.mo_occupations = (
        None if occupation is None else np.array([occupation], dtype=np.float64)
    )
    mo.basis_set_ref = basis_set_ref

    # Optional: stash the index as symmetry label so it shows up in GUI labels.
    if mo_index is not None:
        mo.mo_symmetry = np.array([str(mo_index)], dtype=object)

    grid = {
        'values': values,
        'origin': origin,
        'voxel_vectors': voxel_vectors,
        'shape': shape,
        # Provide atom positions to aid downstream validation/visualization
        'atomic_numbers': atoms.get_atomic_numbers(),
        'positions_bohr': atoms.get_positions(),  # ASE cube reader already returns Bohr
    }

    return mo, grid
