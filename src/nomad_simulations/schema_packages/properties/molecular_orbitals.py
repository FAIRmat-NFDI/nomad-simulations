import itertools
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import URL, MEnum, Quantity, SectionProxy, SubSection

from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.variables import Variables


class MolecularOrbitals(PhysicalProperty):
    """
    Molecular-orbital eigenstates expressed in an atomic-orbital basis,
    using the standard α/β spin-channel convention from MolSSI QCSchema
    and TREXIO:

    • One instance per spin channel:
      - spin_channel = 0 : α-spin orbitals
      - spin_channel = 1 : β-spin orbitals
    • RHF/RKS (closed-shell): instantiate once with spin_channel=0
    • UHF/UKS (unrestricted): instantiate two objects, α then β
    • Shape conventions (per instance):
      - energies:      array of length n_mo (orbital energies εᵢ)
      - occupations:  array of length n_mo (occupations nᵢ: 0,1 or 2)
      - coefficients: matrix shape [n_mo x n_ao] (AO→MO expansion Cᵢμ)

    References for this pattern:
      — MolSSI QCSchema Wavefunction: separate orbitals_a, orbitals_b arrays
      — TREXIO mo_coeff_up / mo_coeff_dn groups

    Quantities:
      spin_channel    (int): 0=α, 1=β
      n_mo            (int): number of MOs
      mo_energies     (float[joule][n_mo])
      mo_occupations  (float[n_mo])
      mo_coefficients (float[n_mo, n_ao])
      mo_type         (enum): canonical, natural, localized, …
    """

    # reference to the AO basis in which these MOs are expressed
    basis_set_ref = Quantity(
        type=SectionProxy('AtomCenteredBasisSet'),
        description="""
        The atom-centered basis set used for these molecular orbitals.
        """,
    )

    # spin channel: 0=alpha, 1=beta (for closed‐shell can omit or set both)
    spin_channel = Quantity(
        type=np.int32,
        description="""
        Spin index of these orbitals: 0 (alpha) or 1 (beta).  
        For closed-shell (RHF/RKS) you may store only channel 0.
        """,
    )

    n_mo = Quantity(
        type=np.int32,
        description='Number of molecular orbitals stored.',
    )

    n_ao = Quantity(
        type=np.int32,
        description='Number of atomic orbitals (size of AO basis).',
    )

    mo_energies = Quantity(
        type=np.float64,
        unit='joule',
        shape=['n_mo'],
        description="""
        Orbital energies for each MO.  In a canonical SCF these are the eigenvalues 
        of the (Fock) Hamiltonian; in post-processing they may be natural-orbital energies.
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

    mo_coefficients = Quantity(
        type=np.float64,
        shape=['n_mo', 'n_ao'],
        description="""
        The AO→MO coefficient matrix **C**, such that 
        ψ_i(r) = ∑_μ C[i,μ] φ_μ(r).  
        Row index i runs over MOs, column index μ runs over AOs in `basis_set_ref`.
        """,
    )

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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # infer sizes
        if self.mo_energies is not None:
            self.n_mo = len(self.mo_energies)
        if self.mo_coefficients is not None:
            # ensure consistent dimensions
            nm, na = self.mo_coefficients.shape
            if self.n_mo is None:
                self.n_mo = nm
            if self.n_ao is None:
                self.n_ao = na
            if (nm != self.n_mo) or (na != self.n_ao):
                raise ValueError(
                    f'Inconsistent MO coefficient shape: '
                    f'got {nm}×{na}, expected {self.n_mo}×{self.n_ao}.'
                )

        # shape‐check energies & occupations
        if self.mo_energies is not None and len(self.mo_energies) != self.n_mo:
            raise ValueError('Length of `mo_energies` must equal `n_mo`.')
        if self.mo_occupations is not None and len(self.mo_occupations) != self.n_mo:
            raise ValueError('Length of `mo_occupations` must equal `n_mo`.')
