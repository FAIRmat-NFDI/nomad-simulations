from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
import pint
from nomad.config import config
from nomad.datamodel.hdf5 import HDF5Dataset, HDF5Wrapper
from nomad.metainfo import MEnum, Quantity, Reference, SectionProxy

from nomad_simulations.schema_packages.data_types import (
    Bound,
    m_float_bounded,
    strictly_positive_int,
)
from nomad_simulations.schema_packages.physical_property import PhysicalProperty

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class MolecularOrbitals(PhysicalProperty):
    """
    Molecular-orbital eigenstates in an atom-centered AO basis.

    `spin_channel` selects the representation: set (0=alpha, 1=beta) gives spin
    orbitals with occupations in [0,1]; unset gives spin-summed spatial orbitals
    with occupations in [0,2]. `coefficients`, `value`, `occupations`, `role`,
    `symmetry` describe the same `n_mo` orbitals. `value` holds the orbital
    energies (eigenvalues), defined only for `kind=canonical`. `n_mo` is at most
    `n_ao`.
    """

    n_mo = Quantity(
        type=strictly_positive_int(),
        description="""Number of molecular orbitals.""",
    )

    value = Quantity(
        type=np.float64,
        unit='joule',
        shape=['n_mo'],
        description="""
        Orbital energies (eigenvalues) for each molecular orbital, mirroring
        `ElectronicEigenvalues.value`. Defined only for `kind=canonical`; may be
        absent for natural/localized orbitals.
        """,
    )

    occupations = Quantity(
        type=m_float_bounded(
            dtype=np.float64,
            bound=Bound(
                '[0,2]',
                slack=configuration.mo_occupation_slack,
                on_violation='log',
                clamp=True,
            ),
        ),
        shape=['n_mo'],
        description="""
        Occupation number for each molecular orbital. Expected in [0, 2] (spin-summed;
        [0, 1] for spin orbitals). Occupation numbers from approximate methods (e.g.
        MP2/CC natural orbitals) can fall slightly outside; values beyond the
        `mo_occupation_slack` tolerance are logged, and out-of-[0, 2] values are clamped
        into [0, 2].
        """,
    )

    spin_channel = Quantity(
        type=np.int32,
        description="""Spin channel of the molecular orbitals: 0 for α-spin, 1 for β-spin.""",
    )

    # AO basis metadata
    n_ao = Quantity(
        type=strictly_positive_int(),
        description="""Number of atomic orbitals (size of the AO basis).""",
    )

    basis_set_ref = Quantity(
        type=Reference(
            SectionProxy(
                'nomad_simulations.schema_packages.basis_set.AtomCenteredBasisSet'
            )
        ),
        description="""Reference to the atom-centered basis set used to expand these orbitals.""",
    )

    # AO → MO coefficient matrix
    coefficients = Quantity(
        type=HDF5Dataset,
        shape=[],
        description="""
        The AO→MO coefficient matrix **C**, such that
        ψ_i(r) = ∑_μ C[i,μ] φ_μ(r).
        Row index i runs over MOs (`n_mo`), column index μ runs over AOs (`n_ao`).
        Expected dataset shape: [`n_mo`, `n_ao`].
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
        Expected dataset shape: [`n_mo`, `n_ao`].
        """,
    )

    # Per-orbital classification
    role = Quantity(
        type=MEnum('core', 'inactive', 'active', 'virtual', 'deleted'),
        shape=['n_mo'],
        description="""
        Role of each MO within a correlated calculation or active-space protocol:

        * core: fully occupied, energy-frozen, excluded from correlation.
        * inactive: fully occupied, variationally optimized, outside the active space.
        * active: in the active space.
        * virtual: unoccupied correlated orbital.
        * deleted: pruned for technical reasons (e.g. linear dependence).

        `role` is the active-space/correlation classification, orthogonal to `occupations`.
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
        type=MEnum('canonical', 'natural', 'localized'),
        description="""
        Classification of the orbital set by the transformation that defines it:

        * canonical  : standard SCF eigenfunctions (Fock/Kohn-Sham diagonal)
        * natural    : eigenfunctions of the 1-RDM
        * localized  : after a localization transform (Boys, Pipek-Mezey, …)

        For MCSCF/CASSCF outputs, tag the reported set as `canonical` or `natural`
        (whichever it is); the active-space partition is captured by `role`.
        """,
    )

    # Frontier-orbital energies as reported by the code (provenance-preserving).
    # Set by parsers and never touched during normalization. The `_normalized`
    # counterparts below are derived independently from the orbital data; they do
    # not fall back to these parsed values.
    homo_parsed = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Highest occupied molecular orbital (HOMO) energy as reported by the code.
        """,
    )

    lumo_parsed = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Lowest unoccupied molecular orbital (LUMO) energy as reported by the code.
        """,
    )

    # TODO(#467): the parsed-vs-derived provenance of the gap is better expressed
    # via `is_derived` on a dedicated `ElectronicBandGap` PhysicalProperty than via
    # a strictly-parsed quantity here.
    homo_lumo_gap_parsed = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        HOMO-LUMO gap as directly reported by the code. Strictly a parsed value, **not**
        derived from `homo_parsed`/`lumo_parsed`. Leave unset if the code reports no
        gap directly.
        """,
    )

    # Derived frontier-orbital energies (canonical orbitals only). Resolved purely
    # from `value` and `occupations` during normalization; left unset when the
    # occupied/unoccupied boundary cannot be resolved, with no fallback to the
    # parsed counterparts.
    homo_normalized = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Highest occupied molecular orbital (HOMO) energy, derived purely from `value`
        and `occupations` for `kind=canonical`. Left unset when the occupied/unoccupied
        boundary cannot be resolved; does **not** fall back to `homo_parsed`.
        """,
    )

    lumo_normalized = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Lowest unoccupied molecular orbital (LUMO) energy, derived purely from `value`
        and `occupations` for `kind=canonical`. Left unset when the occupied/unoccupied
        boundary cannot be resolved; does **not** fall back to `lumo_parsed`.
        """,
    )

    homo_lumo_gap_normalized = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        HOMO-LUMO gap of the derived frontier pair, taken as
        `lumo_normalized - homo_normalized`. Left unset when that pair is unavailable;
        does **not** fall back to `homo_lumo_gap_parsed`.
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
                    self.occupations,
                    self.role,
                    self.symmetry,
                    self.value,
                ):
                    if values is not None:
                        self.n_mo = len(values)
                        break

        if self.n_ao is None and valid_shapes:
            self.n_ao = int(valid_shapes[0][1])

        self._validate_coefficient_shape(coefficient_shape, logger)
        self._validate_coefficient_shape(coefficient_im_shape, logger)
        self._validate_per_orbital_lengths(logger)

        if (
            coefficient_shape is not None
            and coefficient_im_shape is not None
            and coefficient_shape != coefficient_im_shape
        ):
            logger.error(
                'The real and imaginary coefficient matrices have different shapes and cannot be combined.'
            )

        if self.spin_channel is not None and self.spin_channel not in (0, 1):
            logger.error('`spin_channel` must be 0 (alpha) or 1 (beta) when set.')

        if self.n_mo is not None and self.n_ao is not None and self.n_mo > self.n_ao:
            logger.error(
                '`n_mo` exceeds `n_ao`, which is physically inconsistent: the MO space cannot be larger than the AO basis it is expanded in.'
            )

        self._resolve_homo_lumo()

    def _resolve_homo_lumo(self) -> None:
        # Frontier orbitals are derived purely from `value` and `occupations`; they
        # never fall back to the parsed values. The gap follows from the derived pair
        # and is therefore always consistent with it.
        homo, lumo = self._derive_frontier_orbitals()
        if homo is not None:
            self.homo_normalized = homo
        if lumo is not None:
            self.lumo_normalized = lumo
        if homo is not None and lumo is not None:
            self.homo_lumo_gap_normalized = lumo - homo

    def _derive_frontier_orbitals(
        self,
    ) -> tuple[pint.Quantity | None, pint.Quantity | None]:
        # Frontier orbitals are well defined only for canonical orbitals with both
        # value (energies) and occupations present and consistent in length. `kind`
        # must be explicitly `canonical`: an unset `kind` is not assumed canonical, so
        # a non-canonical set is never silently mis-resolved into HOMO/LUMO.
        if self.kind != 'canonical':
            return None, None
        if self.value is None or self.occupations is None:
            return None, None
        occupations = np.asarray(self.occupations)
        if len(occupations) != len(self.value):
            return None, None
        occupied = occupations > configuration.mo_occupation_cutoff
        # Need at least one occupied and one unoccupied orbital to define a boundary.
        if not occupied.any() or occupied.all():
            return None, None
        return self.value[occupied].max(), self.value[~occupied].min()

    def _validate_per_orbital_lengths(self, logger: 'BoundLogger') -> None:
        if self.n_mo is None:
            return
        for values in (self.value, self.occupations, self.role, self.symmetry):
            if values is None:
                continue
            if len(values) != self.n_mo:
                logger.error(
                    'Length of a per-orbital quantity does not match `n_mo`; all of `value`, `occupations`, `role`, and `symmetry` must have exactly `n_mo` entries.'
                )

    def _validate_coefficient_shape(
        self, shape: tuple[int, ...] | None, logger: 'BoundLogger'
    ) -> None:
        if shape is None:
            return
        if len(shape) != 2:
            logger.error(
                'The coefficient matrix must be a 2D dataset with shape [`n_mo`, `n_ao`].'
            )
            return
        expected = (self.n_mo, self.n_ao)
        if None not in expected and shape != expected:
            logger.error(
                'Coefficient matrix shape does not match [`n_mo`, `n_ao`]; check that `n_mo` and `n_ao` are consistent with the dataset dimensions.'
            )

    @staticmethod
    def _resolve_dataset_shape(value: Any) -> tuple[int, ...] | None:
        if value is None:
            return None
        if isinstance(value, HDF5Wrapper):
            with value as dataset:
                return tuple(dataset.shape)
        return tuple(value.shape)
