import itertools
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import URL, MEnum, Quantity, Reference, SectionProxy

from nomad_simulations.schema_packages.physical_property import PhysicalProperty


class MolecularOrbitals(PhysicalProperty):
    """
    Molecular-orbital eigenstates expressed in an atom-centred AO basis.

    Every quantity is either directly mappable to the TREXIO *mo* group or
    provides auxiliary metadata needed by NOMAD tooling.  Shapes are expressed
    in Fortran/column-major convention to match TREXIO and most quantum-code
    outputs.

    The TREXIO format:
    Posenitsky et al., J. Chem. Phys. 158, 174801 (2023)

    ----------
    Quantities
    -----------------
    ``basis_set_ref``        Reference to the AO basis section.
    ``mo_spin``              Per-orbital spin index (TREXIO-style unified list).
    ``n_mo``                 Number of molecular orbitals stored.
    ``n_ao``                 Size of the AO basis.
    ``mo_energies``          εᵢ orbital energies (eV).
    ``mo_occupations``       nᵢ occupation numbers.
    ``mo_coefficients``      Real part of AO→MO coefficient matrix C.
    ``mo_coefficients_im``   Imaginary part of C (optional).
    ``mo_class``             Role of each MO: Core/Inactive/Active/Virtual/Deleted.
    ``mo_symmetry``          Irreducible-representation labels (e.g. *a₁*, *b₂*).
    ``mo_type``              Classification of entire set: canonical/natural/…

    """

    # ------------------------------------------------------------------ #
    #                           References                               #
    # ------------------------------------------------------------------ #
    basis_set_ref = Quantity(
        type=Reference(SectionProxy('AtomCenteredBasisSet')),
        description="""
        Reference to the atom-centered basis set in which these molecular
        orbitals are expanded.
        """,
    )

    # ------------------------------------------------------------------ #
    #                    Dimension-defining scalars                      #
    # ------------------------------------------------------------------ #
    n_mo = Quantity(
        type=np.int32,
        description='Number of molecular orbitals stored.',
    )

    n_ao = Quantity(
        type=np.int32,
        description='Number of atomic orbitals (size of AO basis).',
    )

    # ------------------------------------------------------------------ #
    #                   Per-orbital mandatory metadata                   #
    # ------------------------------------------------------------------ #
    mo_spin = Quantity(
        type=np.int32,
        shape=['n_mo'],
        description="""
        Spin index of each molecular orbital: 0 for α-spin, 1 for β-spin.
        """,
    )

    mo_energies = Quantity(
        type=np.float64,
        unit='electron_volt',
        shape=['n_mo'],
        description="""
        Orbital energies for each MO.  In a canonical SCF these are the eigenvalues 
        of the (Fock) Hamiltonian; in correlated frameworks they may be natural-orbital
        energies or any other chosen set.
        """,
    )

    mo_occupations = Quantity(
        type=np.float64,
        shape=['n_mo'],
        description="""
        Occupation numbers for each MO.  Closed-shell codes will typically give 2.0 
        for occupied and 0.0 for virtual orbitals; unrestricted codes use two channels.
        """,
    )

    mo_class = Quantity(
        type=MEnum('core', 'inactive', 'active', 'virtual', 'deleted'),
        shape=['n_mo'],
        description="""
        Role of each MO within a correlated calculation or active-space
        protocol:

        * core     : energy-frozen doubly-occupied  
        * inactive : doubly-occupied but variationally optimised  
        * active   : part of the active space  
        * virtual  : unoccupied (correlated) orbital  
        * deleted  : pruned for technical reasons
        """,
    )

    mo_symmetry = Quantity(
        type=str,
        shape=['n_mo'],
        description="""
        Symmetry label of each MO in the molecule's point group
        (e.g. *a₁*, *b₂u*, *pi_g*). Leave empty for systems with
        no detected symmetry.
        """,
    )

    # ------------------------------------------------------------------ #
    #                 AO → MO coefficient matrices                       #
    # ------------------------------------------------------------------ #
    mo_coefficients = Quantity(
        type=np.float64,
        shape=['n_mo', 'n_ao'],
        description="""
        The AO→MO coefficient matrix **C**, such that 
        ψ_i(r) = ∑_μ C[i,μ] φ_μ(r).  
        Row index i runs over MOs, column index μ runs over AOs in `basis_set_ref`.
        """,
    )

    mo_coefficients_im = Quantity(
        type=np.float64,
        shape=['n_mo', 'n_ao'],
        description="""
        Imaginary component of the AO→MO coefficient matrix **C**.  
        Combine it with `mo_coefficients` to obtain the full complex matrix:
            C_complex = mo_coefficients + 1j * mo_coefficients_im  
        Leave this quantity unset (or an empty array) when the wave-function
        is strictly real, as in non-relativistic γ-point calculations.
        """,
    )

    # ------------------------------------------------------------------ #
    #               Whole-set classification (free-text tag)             #
    # ------------------------------------------------------------------ #
    mo_type = Quantity(
        type=MEnum('canonical', 'natural', 'localized', 'hybrid'),
        default='canonical',
        description="""
        Classification of these orbitals:
          - canonical  : standard SCF eigenfunctions
          - natural    : eigenfunctions of the 1-RDM
          - localized  : after a localization transform (Boys, Pipek-Mezey, …)
          - hybrid     : e.g. post-HF (CASSCF) orbitals, etc.
        """,
    )
