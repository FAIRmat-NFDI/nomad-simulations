import itertools
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.hdf5 import HDF5Dataset, HDF5Wrapper
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import URL, MEnum, Quantity, Reference, SectionProxy

from nomad_simulations.schema_packages.properties import ElectronicEigenvalues


class MolecularOrbitals(ElectronicEigenvalues):
    """
    Molecular-orbital eigenstates expressed in an atom-centred AO basis.

    Every quantity is either directly mappable to the TREXIO *mo* group or
    provides auxiliary metadata needed by NOMAD tooling.

    The TREXIO format:
    Posenitsky et al., J. Chem. Phys. 158, 174801 (2023).
    """

    # References
    basis_set_ref = Quantity(
        type=Reference(
            SectionProxy(
                'nomad_simulations.schema_packages.basis_set.AtomCenteredBasisSet'
            )
        ),
        description="""
        Reference to the atom-centered basis set in which these molecular
        orbitals are expanded.
        """,
    )

    # Dimension-defining scalars
    n_mo = Quantity(
        type=np.int32,
        description='Number of molecular orbitals stored.',
    )

    n_ao = Quantity(
        type=np.int32,
        description='Number of atomic orbitals (size of AO basis).',
    )

    # Per-orbital mandatory metadata
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
        Orbital energies for each MO. In a canonical SCF these are the eigenvalues 
        of the (Fock) Hamiltonian; in correlated frameworks they may be natural-orbital
        energies or any other chosen set.
        """,
    )

    mo_occupations = Quantity(
        type=np.float64,
        shape=['n_mo'],
        description="""
        Occupation numbers for each MO. Closed-shell codes will typically give 2.0 
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

    # AO → MO coefficient matrices
    mo_coefficients = Quantity(
        type=HDF5Dataset,
        shape=[],
        description="""
        The AO→MO coefficient matrix **C**, such that 
        ψ_i(r) = ∑_μ C[i,μ] φ_μ(r). 
        Row index i runs over MOs, column index μ runs over AOs in `basis_set_ref`.
        The expected dataset shape is [`n_mo`, `n_ao`].
        """,
    )

    mo_coefficients_im = Quantity(
        type=HDF5Dataset,
        shape=[],
        description="""
        Imaginary component of the AO→MO coefficient matrix **C**. 
        Combine it with `mo_coefficients` to obtain the full complex matrix:
            C_complex = mo_coefficients + 1j * mo_coefficients_im  
        Leave this quantity unset when the wave-function
        is strictly real, as is typical in non-relativistic calculations without complex basis functions.
        The expected dataset shape is [`n_mo`, `n_ao`].
        """,
    )

    # Whole-set classification
    mo_type = Quantity(
        type=MEnum('canonical', 'natural', 'localized', 'hybrid'),
        # default='canonical',
        description="""
        Classification of these orbitals:
          - canonical  : standard SCF eigenfunctions
          - natural    : eigenfunctions of the 1-RDM
          - localized  : after a localization transform (Boys, Pipek-Mezey, …)
          - hybrid     : e.g. post-HF (CASSCF) orbitals, etc.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Infer `n_mo` / `n_ao` from supplied arrays when absent.
        """
        super().normalize(archive, logger)

        coefficient_shape = self._resolve_dataset_shape(self.mo_coefficients)
        coefficient_im_shape = self._resolve_dataset_shape(self.mo_coefficients_im)
        valid_coefficient_shapes = [
            shape
            for shape in (coefficient_shape, coefficient_im_shape)
            if shape is not None and len(shape) == 2
        ]

        # ---------- infer n_mo ----------
        if self.n_mo is None:
            if valid_coefficient_shapes:
                self.n_mo = int(valid_coefficient_shapes[0][0])
            elif self.mo_spin is not None:
                self.n_mo = len(self.mo_spin)
            elif self.mo_energies is not None:
                self.n_mo = len(self.mo_energies)

        # ---------- infer n_ao ----------
        if self.n_ao is None and valid_coefficient_shapes:
            self.n_ao = int(valid_coefficient_shapes[0][1])

        self._validate_coefficient_shape(
            'mo_coefficients', coefficient_shape, logger=logger
        )
        self._validate_coefficient_shape(
            'mo_coefficients_im', coefficient_im_shape, logger=logger
        )
        if (
            coefficient_shape is not None
            and coefficient_im_shape is not None
            and coefficient_shape != coefficient_im_shape
        ):
            logger.error(
                '`mo_coefficients_im` shape must match `mo_coefficients`; '
                f'got {coefficient_im_shape} and {coefficient_shape}.'
            )

    def _validate_coefficient_shape(
        self, quantity_name: str, shape: tuple[int, ...] | None, logger: 'BoundLogger'
    ) -> None:
        if shape is None:
            return
        if len(shape) != 2:
            logger.error(
                f'`{quantity_name}` must be a 2D dataset with shape '
                f'[`n_mo`, `n_ao`]; got shape {shape}.'
            )
            return

        expected_shape = (self.n_mo, self.n_ao)
        if None not in expected_shape and shape != expected_shape:
            logger.error(
                f'`{quantity_name}` shape must match [`n_mo`, `n_ao`]; '
                f'got {shape}, expected {expected_shape}.'
            )

    @staticmethod
    def _resolve_dataset_shape(value: Any) -> tuple[int, ...] | None:
        """Return the shape of an in-memory array or HDF5-backed dataset."""
        if value is None:
            return None
        if isinstance(value, HDF5Wrapper):
            with value as dataset:
                return tuple(dataset.shape)
        shape = getattr(value, 'shape', None)
        return tuple(shape) if shape is not None else None
