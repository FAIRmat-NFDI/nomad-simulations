from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
from nomad.datamodel.hdf5 import HDF5Dataset, HDF5Wrapper
from nomad.metainfo import MEnum, Quantity, Reference, SectionProxy

from nomad_simulations.schema_packages.data_types import (
    positive_float,
    strictly_positive_int,
)
from nomad_simulations.schema_packages.physical_property import PhysicalProperty


class MolecularOrbitals(PhysicalProperty):
    """
    Molecular-orbital eigenstates expressed in an atom-centered AO basis.

    For spin-polarized calculations use two separate sections, one per spin channel
    (`spin_channel=0` for α, `spin_channel=1` for β).
    """

    n_mo = Quantity(
        type=strictly_positive_int(),
        description='Number of molecular orbitals.',
    )

    energies = Quantity(
        type=np.float64,
        unit='joule',
        shape=['n_mo'],
        description='Orbital energies for each molecular orbital.',
    )

    occupations = Quantity(
        type=positive_float(),
        shape=['n_mo'],
        description='Occupation number for each molecular orbital.',
    )

    spin_channel = Quantity(
        type=np.int32,
        description='Spin channel of the molecular orbitals: 0 for α-spin, 1 for β-spin.',
    )

    # AO basis metadata
    n_ao = Quantity(
        type=strictly_positive_int(),
        description='Number of atomic orbitals (size of the AO basis).',
    )

    basis_set_ref = Quantity(
        type=Reference(
            SectionProxy(
                'nomad_simulations.schema_packages.basis_set.AtomCenteredBasisSet'
            )
        ),
        description='Reference to the atom-centered basis set used to expand these orbitals.',
    )

    # AO → MO coefficient matrix
    coefficients = Quantity(
        type=HDF5Dataset,
        shape=[],
        description="""
        The AO→MO coefficient matrix **C**, such that
        ψ_i(r) = ∑_μ C[i,μ] φ_μ(r).
        Row index i runs over MOs (n_mo), column index μ runs over AOs (n_ao).
        Expected dataset shape: [n_mo, n_ao].
        """,
    )

    coefficients_im = Quantity(
        type=HDF5Dataset,
        shape=[],
        description="""
        Imaginary component of the AO→MO coefficient matrix.
        Combine with `coefficients` to obtain the full complex matrix:
            C_complex = coefficients + 1j * coefficients_im
        Omit for strictly real wave functions (non-relativistic calculations
        without complex basis functions).
        Expected dataset shape: [n_mo, n_ao].
        """,
    )

    # Per-orbital classification
    role = Quantity(
        type=MEnum('core', 'inactive', 'active', 'virtual', 'deleted'),
        shape=['n_mo'],
        description="""
        Role of each MO within a correlated calculation or active-space protocol:

        * core     : energy-frozen doubly-occupied
        * inactive : doubly-occupied but variationally optimised
        * active   : part of the active space
        * virtual  : unoccupied (correlated) orbital
        * deleted  : pruned for technical reasons
        """,
    )

    symmetry = Quantity(
        type=str,
        shape=['n_mo'],
        description="""
        Symmetry label of each MO in the molecule's point group
        (e.g. a₁, b₂u, π_g). Leave empty for systems with no detected symmetry.
        """,
    )

    # Whole-set classification
    kind = Quantity(
        type=MEnum('canonical', 'natural', 'localized', 'hybrid'),
        description="""
        Classification of the orbital set:

        * canonical  : standard SCF eigenfunctions
        * natural    : eigenfunctions of the 1-RDM
        * localized  : after a localization transform (Boys, Pipek-Mezey, …)
        * hybrid     : post-HF orbitals, e.g. CASSCF
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        coefficient_shape = self._resolve_dataset_shape(self.coefficients)
        coefficient_im_shape = self._resolve_dataset_shape(self.coefficients_im)
        valid_shapes = [
            s
            for s in (coefficient_shape, coefficient_im_shape)
            if s is not None and len(s) == 2
        ]

        if self.n_mo is None:
            if valid_shapes:
                self.n_mo = int(valid_shapes[0][0])
            else:
                for values in (
                    self.energies,
                    self.occupations,
                    self.role,
                    self.symmetry,
                ):
                    shape = getattr(values, 'shape', None)
                    if shape is not None and len(shape) > 0:
                        self.n_mo = int(shape[0])
                        break
                    if values is not None:
                        self.n_mo = len(values)
                        break

        if self.n_ao is None and valid_shapes:
            self.n_ao = int(valid_shapes[0][1])

        self._validate_coefficient_shape('coefficients', coefficient_shape, logger)
        self._validate_coefficient_shape(
            'coefficients_im', coefficient_im_shape, logger
        )
        self._validate_per_orbital_lengths(logger)

        if (
            coefficient_shape is not None
            and coefficient_im_shape is not None
            and coefficient_shape != coefficient_im_shape
        ):
            logger.error(
                'Molecular orbital coefficient shapes do not match.',
                coefficients_shape=coefficient_shape,
                coefficients_im_shape=coefficient_im_shape,
            )

    def _validate_per_orbital_lengths(self, logger: 'BoundLogger') -> None:
        if self.n_mo is None:
            return
        for quantity_name in (
            'energies',
            'occupations',
            'role',
            'symmetry',
        ):
            values = getattr(self, quantity_name)
            if values is None:
                continue
            shape = getattr(values, 'shape', None)
            length = (
                int(shape[0]) if shape is not None and len(shape) > 0 else len(values)
            )
            if length != self.n_mo:
                logger.error(
                    'Molecular orbital quantity length does not match n_mo.',
                    quantity_name=quantity_name,
                    length=length,
                    expected_length=self.n_mo,
                )

    def _validate_coefficient_shape(
        self, quantity_name: str, shape: tuple[int, ...] | None, logger: 'BoundLogger'
    ) -> None:
        if shape is None:
            return
        if len(shape) != 2:
            logger.error(
                'Molecular orbital coefficients must be a 2D dataset.',
                quantity_name=quantity_name,
                shape=shape,
            )
            return
        expected = (self.n_mo, self.n_ao)
        if None not in expected and shape != expected:
            logger.error(
                'Molecular orbital coefficient shape does not match expected shape.',
                quantity_name=quantity_name,
                shape=shape,
                expected_shape=expected,
            )

    @staticmethod
    def _resolve_dataset_shape(value: Any) -> tuple[int, ...] | None:
        if value is None:
            return None
        if isinstance(value, HDF5Wrapper):
            with value as dataset:
                return tuple(dataset.shape)
        shape = getattr(value, 'shape', None)
        return tuple(shape) if shape is not None else None
