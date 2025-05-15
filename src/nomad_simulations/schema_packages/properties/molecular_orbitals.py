import itertools
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import URL, MEnum, Quantity, SectionProxy, SubSection

from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.variables import Variables


class MOIndex(Variables):
    """
    Discrete index for molecular orbitals (0-based).
    """

    points = Quantity(
        type=np.int32,
        shape=['n_points'],
        description="""
        Orbital indices from 0 to n_mo-1.
        """,
    )

    def __init__(self, m_def=None, m_context=None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name


class AOIndex(Variables):
    """
    Discrete index for atomic orbitals (0-based) matching the AO basis.
    """

    points = Quantity(
        type=np.int32,
        shape=['n_points'],
        description="""
        Atomic-orbital indices from 0 to n_ao-1, in the order of `basis_set_ref`.
        """,
    )

    def __init__(self, m_def=None, m_context=None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name


class MolecularOrbitals(PhysicalProperty):
    """
    Molecular-orbital eigenstates expressed in an atomic-orbital basis,
    using the standard α/β spin-channel convention from MolSSI QCSchema
    and TREXIO.

    Variables:
      - MOIndex: index over molecular orbitals
      - AOIndex: index over atomic orbitals

    Quantities:
      spin_channel    (int): 0=α, 1=β
      n_mo            (int): number of MOs
      mo_energies     (float[joule][n_mo])
      mo_occupations  (float[n_mo])
      mo_coefficients (float[n_mo, n_ao])
      mo_type         (enum): canonical, natural, localized, …
    """

    # attach two variables: MOIndex then AOIndex
    variables = SubSection(sub_section=Variables.m_def, repeats=True)

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

    # main coefficient matrix: C[i, mu]
    value = Quantity(
        type=np.float64,
        shape=['*', '*'],
        description='AO→MO coefficients matrix, dims [n_mo, n_ao].',
    )

    mo_energies = Quantity(
        type=np.float64,
        unit='joule',
        shape=['*'],
        description='Orbital energies ε_i matching MOIndex dimension.',
    )

    mo_occupations = Quantity(
        type=np.float64,
        shape=['*'],
        description='Occupation numbers n_i matching MOIndex dimension.',
    )

    # mo_coefficients = Quantity(
    #     type=np.float64,
    #     shape=['n_mo', 'n_ao'],
    #     description="""
    #     The AO→MO coefficient matrix **C**, such that
    #     ψ_i(r) = ∑_μ C[i,μ] φ_μ(r).
    #     Row index i runs over MOs, column index μ runs over AOs in `basis_set_ref`.
    #     """,
    # )

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

        # Expect exactly two variables in order: MOIndex, AOIndex
        if not self.variables or len(self.variables) != 2:
            logger.warning(
                'MolecularOrbitals.variables must contain MOIndex and AOIndex'
            )

        mo_var, ao_var = self.variables
        n_mo = mo_var.get_n_points(logger)
        n_ao = ao_var.get_n_points(logger)

        # Check coefficient matrix shape
        if self.value is not None and self.value.shape != (n_mo, n_ao):
            logger.warning(
                f'Coefficient matrix shape {self.value.shape} does not match [n_mo={n_mo}, n_ao={n_ao}].'
            )

        # Check energies and occupations
        if self.mo_energies is not None and len(self.mo_energies) != n_mo:
            logger.warning(
                f'Length of mo_energies ({len(self.mo_energies)}) != n_mo ({n_mo}).'
            )
        if self.mo_occupations is not None and len(self.mo_occupations) != n_mo:
            logger.warning(
                f'Length of mo_occupations ({len(self.mo_occupations)}) != n_mo ({n_mo}).'
            )
