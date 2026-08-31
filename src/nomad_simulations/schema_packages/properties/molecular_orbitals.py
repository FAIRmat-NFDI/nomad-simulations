from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_simulations.schema_packages.outputs import Outputs

import numpy as np
import pint
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.hdf5 import HDF5Dataset, HDF5Wrapper
from nomad.metainfo import MEnum, Quantity, Reference, SectionProxy, SubSection

from nomad_simulations.schema_packages.data_types import (
    Bound,
    m_float_bounded,
    positive_float,
    strictly_positive_int,
)
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.utils import resolve_frontier_levels

# Tolerance on occupation numbers, used in two places: an orbital with occupation
# below this threshold counts as unoccupied when resolving frontier (HOMO/LUMO)
# orbitals; and it widens the accepted interval of the `occupations` datatype so
# floating-point noise just outside [0, 2] is not rejected.
_OCCUPATION_TOL = 1e-6


class FrontierLevels(ArchiveSection):
    """
    HOMO/LUMO pair of a molecular-orbital set, further refining its parent
    `MolecularOrbitals` by singling out the frontier (highest-occupied / lowest-unoccupied)
    levels from the full orbital set. Packaged under `MolecularOrbitals` because the
    frontier levels are derived from the MOs and used in their visualization, rather than
    being searchable in their own right. `is_derived` is `False` for a code-reported pair
    and `True` for one resolved from the orbital data.
    """

    homo = Quantity(
        type=np.float64,
        unit='joule',
        description="""Highest occupied molecular orbital (HOMO) energy.""",
    )

    lumo = Quantity(
        type=np.float64,
        unit='joule',
        description="""Lowest unoccupied molecular orbital (LUMO) energy.""",
    )

    is_derived = Quantity(
        type=bool,
        default=False,
        description="""
        `False` if the pair is directly reported by the code; `True` if resolved from
        `MolecularOrbitals.value` and `MolecularOrbitals.occupations`.
        """,
    )


class MOGap(PhysicalProperty):
    """
    HOMO-LUMO gap of a molecular-orbital set.

    Provenance flows gap -> source: `derived_from` back-references the `FrontierLevels`
    pair the gap was computed from. A code-reported (parsed) gap leaves it unset; the
    referenced pair's own `is_derived` then distinguishes a gap derived from the parsed
    frontier from one derived from the resolved frontier.
    """

    spin_channel = Quantity(
        type=np.int32,
        description="""Spin channel of the gap: 0 for alpha, 1 for beta, when set.""",
    )

    value = Quantity(
        type=positive_float(),
        unit='joule',
        description="""The HOMO-LUMO gap. Non-negative; a crossed frontier pair yields 0.""",
    )

    derived_from = Quantity(
        type=Reference(FrontierLevels.m_def),
        description="""
        Back-reference to the `FrontierLevels` pair this gap was computed from. Unset for a
        code-reported (parsed) gap. The referenced pair's `is_derived` distinguishes a gap
        derived from the parsed frontier from one derived from the resolved frontier.
        """,
    )

    def _is_derived(self) -> bool:
        # A gap with a `derived_from` source is by definition derived; parsed gaps leave it unset.
        return self.derived_from is not None or super()._is_derived()


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

    # Interval [0, 2] (spin-summed maximum) widened by `_OCCUPATION_TOL` slack, so
    # small floating-point noise is accepted while gross violations raise a type
    # error. The spin-resolved maximum (1 for spin orbitals) and a soft-log failure
    # mode are deferred to the interval-datatype work (see TODO in `normalize`).
    occupations = Quantity(
        type=m_float_bounded(
            dtype=np.float64,
            bound=Bound(f'[{-_OCCUPATION_TOL:.7f},{2.0 + _OCCUPATION_TOL:.7f}]'),
        ),
        shape=['n_mo'],
        description="""
        Occupation number for each molecular orbital. Constrained to the interval
        [0, 2] (spin-summed maximum) with a small slack for numerical noise; values
        outside raise a type error.
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

    frontier_levels = SubSection(
        sub_section=FrontierLevels.m_def,
        repeats=True,
        description="""
        HOMO/LUMO frontier pairs for this orbital set: at most one code-reported pair
        (`is_derived=False`, set by the parser) and one resolved pair (`is_derived=True`,
        set during normalization). The derived gap(s) in `Outputs.molecular_orbital_gaps`
        back-reference the pair they were computed from.
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
        # TODO(#468): occupation bounds are now enforced by the `occupations` interval
        # datatype, which raises a hard type-error on violation. Reapply soft logging
        # (a `logger.error` instead of raising) and the spin-resolved upper bound
        # (1 for spin orbitals, 2 for spin-summed) once the interval datatype supports
        # a configurable log failure mode and per-instance bounds.

        if self.n_mo is not None and self.n_ao is not None and self.n_mo > self.n_ao:
            logger.error(
                '`n_mo` exceeds `n_ao`, which is physically inconsistent: the MO space cannot be larger than the AO basis it is expanded in.'
            )

        self._resolve_homo_lumo()

    def _resolve_homo_lumo(self) -> None:
        """Derive this set's frontier pair and gap(s) and store them in `Outputs`.

        For canonical orbitals the frontier pair is resolved from `value`+`occupations`
        into a resolved `FrontierLevels` and its normalized `MOGap`; a `MOGap` is also
        emitted from any parser-provided (parsed) pair. The parsed pair and the directly
        reported gap, when present, are written by the parser -- this only derives.
        """
        outputs = self.m_parent
        if outputs is None:
            return

        if self.kind == 'canonical':
            homo, lumo = resolve_frontier_levels(
                self.value, self.occupations, _OCCUPATION_TOL
            )
            if homo is not None and lumo is not None:
                resolved = self._ensure_frontier(homo, lumo)
                self._emit_gap(outputs, resolved)

        parsed = self._parsed_frontier()
        if parsed is not None and None not in (parsed.homo, parsed.lumo):
            self._emit_gap(outputs, parsed)

    def _ensure_frontier(
        self, homo: pint.Quantity, lumo: pint.Quantity
    ) -> FrontierLevels:
        """Get-or-create this set's resolved (`is_derived=True`) `FrontierLevels`. Returns
        the existing resolved pair if one is already present -- so re-normalization never
        duplicates it -- otherwise creates one from `homo`/`lumo`, appends it, and returns
        it. Coexists with any parser-provided parsed pair (`is_derived=False`).
        """
        for frontier in self.frontier_levels:
            if frontier.is_derived:
                return frontier
        resolved = FrontierLevels(homo=homo, lumo=lumo, is_derived=True)
        self.frontier_levels.append(resolved)
        return resolved

    def _parsed_frontier(self) -> 'FrontierLevels | None':
        """Look up this set's parser-provided (`is_derived=False`) `FrontierLevels`, or
        `None` if the code reported no frontier pair. Pure lookup: unlike `_ensure_frontier`
        it never creates a pair -- parsed pairs come only from the parser.
        """
        return next((f for f in self.frontier_levels if not f.is_derived), None)

    def _emit_gap(self, outputs: 'Outputs', frontier: FrontierLevels) -> None:
        """Emit into `Outputs.molecular_orbital_gaps` an `MOGap` derived from `frontier`,
        at most once per source. The gap value is `lumo - homo`, clamped to 0 for a
        crossed pair. `is_derived` is set explicitly because the emitted gap may never
        have its own `normalize` (and thus the base auto-set from `derived_from`) invoked.

        Idempotency is keyed on the source's `m_path` rather than object identity: on
        reprocessing the archive is reloaded and `derived_from` resolves to a fresh
        object, so an identity check would re-emit the gap on every pass.
        """
        frontier_path = frontier.m_path()
        if any(
            gap.derived_from is not None and gap.derived_from.m_path() == frontier_path
            for gap in outputs.molecular_orbital_gaps
        ):
            return
        gap_value = frontier.lumo - frontier.homo
        if gap_value.magnitude < 0:
            gap_value = 0.0 * frontier.lumo.u
        outputs.molecular_orbital_gaps.append(
            MOGap(
                value=gap_value,
                spin_channel=self.spin_channel,
                derived_from=frontier,
                is_derived=True,
            )
        )

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
