from typing import TYPE_CHECKING, Any

import ase
import numpy as np
import pint
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import MEnum, Quantity, SectionProxy, SubSection
from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.context import Context
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.data_types import (
    positive_float,
    positive_int,
    strictly_positive_int,
    unit_float,
)
from nomad_simulations.schema_packages.utils import log

# @JFRudzinski: TODO rename this file particles_state.py or place ParticleState in model_system.py
# @JFRudzinski: TODO and make separate module files for AtomsState, CGBeadState, etc.


class BaseSpinOrbitalState(Entity):
    n_quantum_number = Quantity(
        type=strictly_positive_int(),
        description="""
        Principal quantum number (n) of the electronic state. Must be > 0.
        """,
    )

    @property
    def _name(self) -> str:
        raise NotImplementedError('Subclasses must implement this method.')

    @property
    def _degeneracy(self) -> int:
        raise NotImplementedError('Subclasses must implement this method.')


class SphericalSymmetryState(
    BaseSpinOrbitalState
):  # @EBB2675 we could also split this section into 3 mutually inheriting sections
    """Describes a quantum state under spherical symmetry.
    Supports SOC and relativistic effects."""

    # TODO: define when these quantities are populated and `None` semantics

    kappa_quantum_number = Quantity(
        type=np.int32, description='κ = ±(j + 1/2), encodes l and j'
    )  # ? should this be mutually exclusive with j_quantum_number?

    j_quantum_number = Quantity(
        type=np.float64,
        shape=['1..2'],
        description="""
        Total angular momentum quantum number $j = |l-s| ... l+s$. Necessary with strong
        L-S coupling or non-collinear spin systems.
        """,
    )

    l_quantum_number = Quantity(
        type=positive_int(),
        description="""
        Angular quantum number of the orbital state. Must be >= 0.
        """,
    )

    l_quantum_symbol = Quantity(
        type=MEnum('s', 'p', 'd', 'f'),
        description="""
        Symbolic representation of the `l` quantum number, i.e., 's', 'p', 'd', 'f'.
        """,
    )  # @EBB2675: do we want to serialize symbolic representations? or maybe just provide a setter / getter mapping?

    mj_quantum_number = Quantity(
        type=np.float64,
        shape=['*'],
        description="""
        Azimuthal projection of the `j$ vector. Necessary with strong L-S coupling or
        non-collinear spin systems.
        """,
    )

    ml_quantum_number = Quantity(
        type=np.int32,
        description="""
        Azimuthal projection number of the `l` vector.
        """,
    )

    ml_quantum_symbol = Quantity(
        type=MEnum(
            'x',
            'y',
            'z',
            'xy',
            'xz',
            'z^2',
            'yz',
            'x^2-y^2',
            'x(x^2-3y^2)',
            'xyz',
            'xz^2',
            'z^3',
            'yz^2',
            'z(x^2-y^2)',
            'y(3x^2-y^2)',
        ),
        description="""
        Symbolic representation of the `ml` quantum number, e.g., 'y', 'xz', 'x^2-y^2'.
        """,
    )  # @EBB2675: do we want to serialize symbolic representations? or maybe just provide a setter / getter mapping?

    s_quantum_number = Quantity(
        type=np.float64,
        default=0.5,
        description="""
        Total spin quantum number $s = 0, 1/2, 1, ...$.
        """,
    )

    ms_quantum_number = Quantity(
        type=np.float64,
        default=0.5,
        description="""
        Azimuthal projection of the $s$ vector.
        """,
    )  # @EBB2675 this, `(-, +)`, `(-1/2, +1/2)`, or `(-1, 1)`?

    ms_quantum_symbol = Quantity(
        type=MEnum('down', 'up'),
        description="""
        Symbolic representation of the `ms` quantum number, e.g., 'down', 'up'.
        """,
    )  # @EBB2675: do we want to serialize symbolic representations? or maybe just provide a setter / getter mapping?

    coupling_origin = Quantity(
        type=MEnum('pure_LS', 'pure_jj', 'intermediate', 'relativistic'),
        description='How this j value was derived',
    )

    @property
    def _degeneracy(self) -> int:
        """
        Compute the degeneracy for this spherical-symmetry state using available
        quantum numbers. If insufficient information is available, returns 0.

        Rules:
        - If j is present (especially as a list), use j-based calculation as it represents coupled states
        - Otherwise, if l is known (and ml not), orbital degeneracy = 2*l + 1; if ml is known, = 1
        - If neither j nor ms is known, default spin degeneracy to 1 (updated from 2)
        """
        lqn = getattr(self, 'l_quantum_number', None)
        ml = getattr(self, 'ml_quantum_number', None)
        ms = getattr(self, 'ms_quantum_number', None)
        jqn = getattr(self, 'j_quantum_number', None)
        mj = getattr(self, 'mj_quantum_number', None)

        # Case A: j-based inference (prioritize when j is present)
        if jqn is not None:
            try:
                # If mj is specified, degeneracy equals the number of mj states
                if mj is not None:
                    if hasattr(mj, '__len__'):
                        return len(mj)
                    else:
                        return 1  # Single mj value

                # No mj specified: use j-based calculation for the full manifold
                # Handle both lists and numpy arrays
                if hasattr(jqn, '__len__') and len(jqn) > 1:
                    return int(sum(int(2 * j + 1) for j in jqn))
                # Single j value (scalar or single-element array)
                j_val = jqn[0] if hasattr(jqn, '__len__') else jqn
                return int(2 * j_val + 1)
            except Exception:
                return 0

        # Case B: l-based inference (fallback when j is not present)
        if lqn is not None:
            orbital_degeneracy = 2 * lqn + 1 if ml is None else 1
            spin_degeneracy = 1 if ms is not None else 1  # Default spin degeneracy to 1
            return int(orbital_degeneracy * spin_degeneracy)

        return 0

    def compute_kappa_from_j_l(self, jqn: float, lqn: int) -> int:
        """
        Compute κ quantum number from j and l quantum numbers.

        Args:
            j: Total angular momentum quantum number
            l: Orbital angular momentum quantum number

        Returns:
            κ = -(j + 1/2) if j = l + 1/2, or κ = +(j + 1/2) if j = l - 1/2
        """
        if abs(jqn - (lqn + 0.5)) < 1e-10:  # j = l + 1/2
            return -(int(jqn + 0.5))
        elif abs(jqn - (lqn - 0.5)) < 1e-10:  # j = l - 1/2
            return +(int(jqn + 0.5))
        else:
            raise ValueError(f'Invalid j={jqn} for l={lqn}. Must be l±1/2')

    def compute_j_from_kappa(self, kappa: int) -> float:
        """
        Compute j quantum number from κ.

        Args:
            kappa: Relativistic quantum number (κ ≠ 0)

        Returns:
            j = |κ| - 1/2
        """
        if kappa == 0:
            raise ValueError('κ = 0 is unphysical')
        return abs(kappa) - 0.5

    def compute_l_from_kappa(self, kappa: int) -> int:
        """
        Compute l quantum number from κ.

        Args:
            kappa: Relativistic quantum number

        Returns:
            l = |κ| - 1/2 if κ < 0, or l = κ for κ > 0
        """
        if kappa == 0:
            raise ValueError('κ = 0 is unphysical')
        if kappa < 0:
            return abs(kappa) - 1  # l = |κ| - 1 for κ < 0
        else:
            return kappa  # l = κ for κ > 0

    def validate_kappa_j_relationship(self, logger: 'BoundLogger') -> bool:
        """
        Validate consistency between κ and j quantum numbers using factored computation.

        Returns:
            True if consistent or only one is defined, False if inconsistent
        """
        if self.kappa_quantum_number is not None and self.j_quantum_number is not None:
            try:
                # Use factored computation for validation
                expected_j = self.compute_j_from_kappa(self.kappa_quantum_number)

                # Check if any j value matches expected
                j_values = (
                    self.j_quantum_number
                    if isinstance(self.j_quantum_number, list)
                    else [self.j_quantum_number]
                )
                if not any(abs(j - expected_j) < 1e-10 for j in j_values):
                    logger.error(
                        f'Inconsistent κ={self.kappa_quantum_number} and j={self.j_quantum_number}. '
                        f'Expected j={expected_j}'
                    )
                    return False
            except ValueError as e:
                logger.error(f'Invalid quantum numbers: {e}')
                return False
        return True

    def normalize_kappa_j_consistency(self):
        """
        Ensure κ and j are consistent during normalization using factored computation.
        Populates missing values when possible.
        """
        if self.kappa_quantum_number is not None and self.j_quantum_number is None:
            # Compute j from κ
            self.j_quantum_number = [
                self.compute_j_from_kappa(self.kappa_quantum_number)
            ]

        elif self.j_quantum_number is not None and self.kappa_quantum_number is None:
            # Cannot uniquely determine κ from j alone (need l as well)
            # This would need orbital information
            pass

    @log
    def validate_quantum_numbers(self) -> bool:
        """
        Validate the angular momentum quantum numbers (l, ml) by checking if they are physically sensible.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (bool): True if the quantum numbers are physically sensible, False otherwise.
        """
        logger = self.validate_quantum_numbers.__annotations__['logger']

        if self.l_quantum_number is not None and self.l_quantum_number < 0:
            logger.error('The `l_quantum_number` must be >= 0.')
            return False

        if self.ml_quantum_number is not None:
            if self.l_quantum_number is None:
                logger.error('Cannot validate ml without l_quantum_number.')
                return False
            if (
                self.ml_quantum_number < -self.l_quantum_number
                or self.ml_quantum_number > self.l_quantum_number
            ):
                logger.error(
                    'The `ml_quantum_number` must be between `-l_quantum_number` and `l_quantum_number`.'
                )
                return False

        return True

    def resolve_number_and_symbol(
        self, quantum_name: str, quantum_type: str, logger: 'BoundLogger'
    ) -> str | int | None:
        """
        Resolves the quantum number or symbol from the `self._orbitals_map` on the passed `quantum_type`.
        `quantum_type` can be either 'number' or 'symbol'. If the quantum type is not found, then the countertype
        (e.g., quantum_type == 'number' => countertype == 'symbol') is used to resolve it.

        Args:
            quantum_name (str): The quantum name to resolve. Can be 'l', 'ml'.
            quantum_type (str): The type of the quantum name. Can be 'number' or 'symbol'.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[Union[str, int]]): The quantum number or symbol resolved from the orbitals_map.
        """
        if quantum_name not in ['l', 'ml']:
            logger.warning("The quantum_name is not recognized. Try 'l', 'ml'.")
            return None
        if quantum_type not in ['number', 'symbol']:
            logger.warning(
                f"The quantum_type {quantum_type} is not recognized. Try 'number' or 'symbol'."
            )
            return None

        # Check if quantity already exists
        quantity = getattr(self, f'{quantum_name}_quantum_{quantum_type}')
        if quantity is not None:
            return quantity

        # If not, check whether the countertype exists
        _countertype_map = {
            'number': 'symbol',
            'symbol': 'number',
        }
        other_quantity = getattr(
            self, f'{quantum_name}_quantum_{_countertype_map[quantum_type]}'
        )
        if other_quantity is None:
            return None

        # If the counterpart exists, then resolve the quantity from the orbitals_map
        orbital_quantity = self._orbitals_map.get(f'{quantum_name}_{quantum_type}s', {})
        if quantum_name == 'l':
            quantity = orbital_quantity.get(other_quantity)
        elif quantum_name == 'ml':
            if self.l_quantum_number is None:
                return None
            quantity = orbital_quantity.get(self.l_quantum_number, {}).get(
                other_quantity
            )
        return quantity

    def _russell_saunders_j_values(
        self, l_quantum: float, s_quantum: float
    ) -> list[float]:
        """Generate all possible j values: |l - s|, |l - s| + 1, ..., l + s"""
        j_min = abs(l_quantum - s_quantum)
        j_max = l_quantum + s_quantum
        return [j_min + i for i in range(int(j_max - j_min) + 1)]

    def _jj_coupling_single_electron(self, l_quantum: float) -> list[float]:
        """
        Compute j values for single electron jj-coupling: j = l ± 1/2

        Args:
            l_quantum: Orbital angular momentum quantum number

        Returns:
            List of possible j values [l - 1/2, l + 1/2] or [1/2] for l=0
        """
        s_quantum = 0.5  # Electron spin is always 1/2

        if l_quantum == 0:
            return [s_quantum]  # Only j = 1/2 for s orbitals
        else:
            return [l_quantum - s_quantum, l_quantum + s_quantum]

    def _jj_coupling_multi_electron(
        self, electron_configs: list[tuple[float, float]]
    ) -> list[float]:
        """
        Compute total J values for multi-electron jj-coupling.

        Args:
            electron_configs: List of (l_i, j_i) pairs for each electron

        Returns:
            List of possible total J values from coupling all j_i

        Example:
            # Two electrons: (l1=1, j1=1/2) and (l2=2, j2=5/2)
            # Possible J = |1/2 - 5/2|, ..., 1/2 + 5/2 = 2, 3
            electron_configs = [(1, 0.5), (2, 2.5)]
            J_values = _jj_coupling_multi_electron(electron_configs)
        """
        if not electron_configs:
            return []

        if len(electron_configs) == 1:
            return [electron_configs[0][1]]  # Single electron: J = j

        # Start with first electron
        current_J_values = [electron_configs[0][1]]

        # Couple each subsequent electron
        for _, j_i in electron_configs[1:]:
            new_J_values = []
            for J_current in current_J_values:
                # Couple J_current with j_i: |J_current - j_i| ≤ J_new ≤ J_current + j_i
                J_min = abs(J_current - j_i)
                J_max = J_current + j_i

                # Generate all possible J values (in steps of 1)
                J_new = J_min
                while J_new <= J_max + 1e-10:  # Small epsilon for float comparison
                    new_J_values.append(J_new)
                    J_new += 1.0

            current_J_values = new_J_values

        # Remove duplicates and sort
        return sorted(list(set(current_J_values)))

    def _jj_coupling(self, electron_data: list[dict]) -> list[float]:
        """
        Unified jj-coupling method for single or multi-electron systems.

        Args:
            electron_data: List of dicts with electron quantum numbers
                          [{'l': 1, 'j': 0.5}, {'l': 2, 'j': 2.5}, ...]
                          If 'j' not provided, computed from 'l'

        Returns:
            List of possible total J values

        Examples:
            # Single electron
            j_values = _jj_coupling([{'l': 1}])  # Returns [0.5, 1.5]

            # Multi-electron with known j values
            j_values = _jj_coupling([{'l': 1, 'j': 0.5}, {'l': 2, 'j': 2.5}])

            # Multi-electron with computed j values
            j_values = _jj_coupling([{'l': 1}, {'l': 2}])  # Computes all combinations
        """
        if not electron_data:
            return []

        # Handle single electron case
        if len(electron_data) == 1:
            electron = electron_data[0]
            if 'j' in electron:
                return [electron['j']]
            else:
                return self._jj_coupling_single_electron(electron['l'])

        # Multi-electron case: need to handle all possible j combinations
        all_j_combinations = []

        # Generate all possible j values for each electron
        electron_j_possibilities = []
        for electron in electron_data:
            if 'j' in electron:
                electron_j_possibilities.append([electron['j']])
            else:
                electron_j_possibilities.append(
                    self._jj_coupling_single_electron(electron['l'])
                )

        # Generate all combinations of j values
        import itertools

        for j_combination in itertools.product(*electron_j_possibilities):
            electron_configs = [
                (electron_data[i]['l'], j_combination[i])
                for i in range(len(electron_data))
            ]
            total_J_values = self._jj_coupling_multi_electron(electron_configs)
            all_j_combinations.extend(total_J_values)

        # Remove duplicates and sort
        return sorted(list(set(all_j_combinations)))

    def __init__(self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        self._orbitals = {
            -1: dict(zip(range(4), ('s', 'p', 'd', 'f'))),
            0: {0: ''},
            1: dict(zip(range(-1, 2), ('x', 'z', 'y'))),
            2: dict(zip(range(-2, 3), ('xy', 'xz', 'z^2', 'yz', 'x^2-y^2'))),
            3: dict(
                zip(
                    range(-3, 4),
                    (
                        'x(x^2-3y^2)',
                        'xyz',
                        'xz^2',
                        'z^3',
                        'yz^2',
                        'z(x^2-y^2)',
                        'y(3x^2-y^2)',
                    ),
                )
            ),
        }
        self._orbitals_map: dict[str, Any] = {
            'l_symbols': self._orbitals[-1],
            'ml_symbols': {i: self._orbitals[i] for i in range(4)},
            'l_numbers': {v: k for k, v in self._orbitals[-1].items()},
            'ml_numbers': {
                k: {v: k for k, v in self._orbitals[k].items()} for k in range(4)
            },
        }

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if not self.validate_kappa_j_relationship(logger):
            return None

        self.normalize_kappa_j_consistency()


class NonCollinearSpinState(SphericalSymmetryState):  # ? Move to `ElectronicState`
    axis = Quantity(
        type=np.float64,
        shape=['3'],  # add actual size restrictions
        description="""
        The projection axis for non-collinear spin systems.
        Expressed in the axis frame in which `ModelSystem` is defined.
        """,
    )  # ? need to define orientation

    # ? particle_index


# TODO: add `class CrystalFieldState(BaseSpinOrbitalState)`


class ElectronicState(Entity):
    """
    A navigation and projection structure for organizing electronic states in a hierarchical manner.
    This section does NOT describe a quantum state itself - that role belongs to `spin_orbit_state`
    (a `BaseSpinOrbitalState` instance). Instead, `ElectronicState` provides a flexible framework for:

    1. **Hierarchical organization**: Decompose electronic structures into nested levels
       (e.g., Cu atom → 3d manifold → individual d-orbitals)

    2. **Multiple decomposition schemes**: The same electrons can be organized differently
       depending on the physics context:
       - By orbital angular momentum (L-S coupling): dxy, dxz, dyz, dz², dx²-y²
       - By total angular momentum (j-j coupling): j=3/2, j=5/2
       - By crystal field symmetry: t2g, eg

    3. **Projection references**: Other schema sections (DOS, Green's functions, etc.) can
       reference specific parts of the electronic structure for projections and analysis.

    4. **Label inheritance**: Child states inherit partial information from parent levels,
       building up complete quantum state descriptions hierarchically.

    Example hierarchies:

    **Non-correlated system (DFT)** - Full decomposition possible:
    ```
    ElectronicState(name="Cu 3d", spin_orbit_state=SphericalSymmetryState(n=3, l=2))
        ├─ ElectronicState(name="dxy", spin_orbit_state=SphericalSymmetryState(ml=-2))
        │   ├─ ElectronicState(name="dxy ↑", spin_orbit_state=SphericalSymmetryState(ms=+0.5), occupation=1.0)
        │   └─ ElectronicState(name="dxy ↓", spin_orbit_state=SphericalSymmetryState(ms=-0.5), occupation=1.0)
        ├─ ElectronicState(name="dxz", ...)
        └─ ...
    ```

    **Correlated system (DMFT)** - No decomposition, just reference:
    ```
    ElectronicState(name="Cu 3d correlated",
                   spin_orbit_state=SphericalSymmetryState(n=3, l=2),
                   occupation=8.5)  # Fractional occupation from many-body state
        # NO sub_states - correlated electrons cannot be decomposed!
    ```

    **Crystal field splitting** - Symmetry-based decomposition:
    ```
    ElectronicState(name="3d in octahedral field")
        ├─ ElectronicState(name="t2g", symmetry_label="t2g", degeneracy=6)
        └─ ElectronicState(name="eg", symmetry_label="eg", degeneracy=4)
    ```

    Note: For strongly correlated systems, `sub_states` may be empty or minimal, as the
    many-body wavefunction cannot be expressed as a simple product of single-particle states.
    """

    name = Quantity(
        type=str,
        description="""
        Descriptive name for this electronic state or decomposition level.
        May inherit information from parent levels (e.g., "3d xy spin-up").
        """,
    )

    point_group = Quantity(
        type=str,
        description="""
        Point-group symmetry of the environment relevant for this electronic state.
        Used when decomposing states by crystal field or ligand field symmetry.
        """,
    )

    symmetry_label = Quantity(
        type=str,
        description="""
        Irreducible representation label under the specified point group symmetry.
        Examples: 't2g', 'eg' (octahedral), 'a1g', 'b1g' (tetragonal), etc.
        Used for crystal field or symmetry-adapted decompositions.
        """,
    )

    spin_orbit_state = SubSection(
        section_def=BaseSpinOrbitalState.m_def,
        description="""
        The actual quantum state descriptor at this level of the hierarchy.
        This `BaseSpinOrbitalState` (typically `SphericalSymmetryState`) defines the 
        quantum numbers and properties of the state in a modular fashion.
        Child states in `sub_states` may inherit quantum numbers from this parent descriptor.
        
        For example, if parent has `spin_orbit_state=SphericalSymmetryState(n=3, l=2)`,
        a child might only specify `spin_orbit_state=SphericalSymmetryState(ml=-2)`,
        with n=3, l=2 implied from the parent.
        """,
    )

    degeneracy = Quantity(
        type=np.int32,
        description="""
        The degeneracy of this electronic state level.
        - For single orbitals: typically 1 (if ml, ms specified) or 2*l+1 (orbital only)
        - For manifolds: sum of constituent state degeneracies
        - For symmetry-adapted states: dimension of irreducible representation
        
        Can be computed from `spin_orbit_state` or summed from `sub_states`.
        For correlated systems, represents the many-body state degeneracy.
        """,
    )

    occupation = Quantity(
        type=positive_float(),
        description="""
        Electronic occupation of this state or manifold.
        
        - For decomposable states: sum of occupations in `sub_states`
        - For correlated systems: effective occupation from many-body calculation (can be fractional)
        - For non-interacting: integer or follows Fermi-Dirac distribution
        
        Note: For correlated electrons, fractional occupation does NOT mean partial occupancy
        of individual orbitals, but rather reflects the many-body quantum state.
        """,
    )

    @property
    def n_sub_states(self) -> int:
        """
        The number of sub-states defined in `sub_states`.
        """
        try:
            return sum(x.n_sub_states for x in self.sub_states)
        except AttributeError:
            return len(self.sub_states)
        except TypeError:
            return 0

    sub_states = SubSection(
        sub_section=SectionProxy('ElectronicState'),
        repeats=True,
        description="""
        Hierarchical decomposition of this electronic state into finer-grained components.
        
        The decomposition can follow different schemes depending on physics context:
        - **Orbital decomposition**: Split by ml quantum number (e.g., p → px, py, pz)
        - **Spin decomposition**: Split by ms quantum number (e.g., orbital → spin up/down)
        - **Symmetry decomposition**: Split by crystal field irreps (e.g., d → t2g, eg)
        - **Coupling scheme**: Split by j,mj for j-j coupling vs. ml,ms for L-S coupling
        
        Multiple decomposition schemes can coexist for the same electrons - choose the one
        appropriate for your analysis. For strongly correlated systems where electrons cannot
        be assigned to individual orbitals, this may be empty or contain only a reference basis.
        
        Child states inherit quantum number information from parent's `spin_orbit_state`,
        only specifying additional refinements (e.g., parent has l=2, child adds ml=-1).
        """,
    )

    atoms_state_ref = SubSection(
        sub_section=SectionProxy('AtomsState'),
        description="""
        Reference to the atomic species (`AtomsState`) to which this electronic state belongs.
        Populated automatically during normalization to link electronic structure to atoms.
        """,
    )

    basis_orbitals = SubSection(
        section_def=BaseSpinOrbitalState.m_def,  # @EBB2675: do you see numerical_settings.basis_set also fit here?
        repeats=True,
        description="""
        References to basis orbitals (as `BaseSpinOrbitalState` instances) used to construct 
        this state as a linear combination.
        
        Used when this electronic state cannot be described by a single quantum state but rather
        as a superposition of simpler orbital states:
        - Hybrid orbitals: sp³ = linear combination of s, px, py, pz orbitals
        - Molecular orbitals: LCAO construction from atomic orbitals
        - Wannier functions: linear combination of Bloch states
        - Symmetry-adapted linear combinations (SALC)
        
        Each entry is a simple quantum state (e.g., `SphericalSymmetryState(n=2, l=0)` for 2s,
        `SphericalSymmetryState(n=2, l=1, ml=1)` for 2px, etc.) without the navigation 
        structure of `ElectronicState`.
        
        The actual expansion coefficients should be stored in the relevant electronic eigenvalue
        sections (e.g., `BandStructure.eigenvectors`, `DOSElectronicNew.value_projection`, etc.)
        rather than duplicated here. This field provides the ordered basis set definition that 
        those coefficients correspond to.
        
        If this state has a simple symmetry description (`spin_orbit_state`), this field 
        is typically empty. It's primarily for composite states that lack simple quantum number labels.
        """,
    )

    def resolve_degeneracy(self) -> int | None:
        """
        Resolve degeneracy for this ElectronicState from `spin_orbit_state._degeneracy`.

        Returns:
            int | None: Computed degeneracy, or None if insufficient information.
        """
        so = getattr(self, 'spin_orbit_state', None)
        if so is None:
            return None

        try:
            deg = so._degeneracy  # Call the property
            if isinstance(deg, int) and deg > 0:
                return deg
        except (AttributeError, Exception):
            # _degeneracy property not implemented or failed
            pass

        return None

    def populate_atoms_state_refs(self, atoms_state: 'AtomsState') -> None:
        """
        Populates the references to the corresponding `AtomsState` definition.

        Args:
            atoms_state (AtomsState): The `AtomsState` instance to reference.
        """
        self.atoms_state_ref = atoms_state
        if self.sub_states:
            for sub_state in self.sub_states:
                sub_state.populate_atoms_state_refs(atoms_state)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve the degeneracy
        if self.degeneracy is None:
            self.degeneracy = self.resolve_degeneracy()

        # Extract name
        if self.name is None:
            if self.spin_orbit_state is not None:
                try:
                    if self.n_quantum_number is not None:
                        self.name = (
                            f'{self.n_quantum_number}{self.spin_orbit_state._name}'
                        )
                    else:
                        self.name = f'{self.spin_orbit_state._name}'
                except AttributeError:
                    # _name property not implemented on this BaseSpinOrbitalState
                    pass


class CoreHole(ElectronicState):
    """
    A section used to define the core-hole state of an atom by extending the `ElectronicState`
    section with core-hole specific properties like excited electron count and DSCF state.
    """

    orbital_ref = SubSection(
        section_def=BaseSpinOrbitalState.m_def,
        description="""
        Reference to the orbital state where the core-hole is generated.
        Can be a single-electron state (SphericalSymmetryState) or a multi-electron state,
        depending on the level of description needed for the vacancy.
        """,
    )  # ? to be merged into spin_orbit_state?

    n_excited_electrons = Quantity(
        type=unit_float(),  # ? too restrictive
        description="""
        The electron charge excited for modelling purposes. This is a number between 0 and 1 (Janak state).
        If `dscf_state` is set to 'initial', then this quantity is set to None (but assumed as excited state).
        """,
    )

    dscf_state = Quantity(
        type=MEnum('initial', 'final'),
        description="""
        Tag used to identify the role in the workflow of the same name. Allowed values are 'initial'
        (not to be confused with the _initial-state approximation_) and 'final'. If 'initial'
        is used, then `n_excited_electrons` is set to None and the `orbital_ref.degeneracy` is
        set to 1.
        """,
    )

    @log
    def resolve_degeneracy(self) -> int | None:
        """
        Resolve degeneracy for this CoreHole from `orbital_ref._degeneracy`.
        Overrides ElectronicState.resolve_degeneracy() to use orbital_ref instead of spin_orbit_state.

        Returns:
            int | None: Computed degeneracy, or None if insufficient information.
        """
        orbital = getattr(self, 'orbital_ref', None)
        if orbital is None:
            return super().resolve_degeneracy()  # Fallback to parent method

        try:
            deg = orbital._degeneracy  # Call the property
            if isinstance(deg, int) and deg > 0:
                return deg
        except (AttributeError, Exception):
            # _degeneracy property not implemented or failed
            pass

        return None

    def resolve_occupation(self, logger: 'BoundLogger') -> np.float64 | None:
        """
        Resolves the occupation of the orbital state. The occupation is resolved from the degeneracy
        and the number of excited electrons.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[np.float64]): The occupation of the active orbital state.
        """

        if (deg := self.resolve_degeneracy()) and self.n_excited_electrons is not None:
            return deg - self.n_excited_electrons
        else:
            logger.warning('Could not resolve degeneracy to compute occupation.')
            return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve the occupation of the active orbital state
        # If dscf_state is 'initial', then n_excited_electrons is set to 0 and occupation should not be set
        if self.dscf_state == 'initial':
            self.n_excited_electrons = 0
            self.degeneracy = 1
            # Don't set occupation for initial state
        else:
            # For other states, resolve occupation normally
            if self.occupation is None:
                self.occupation = self.resolve_occupation(logger=logger)


class HubbardInteractions(ElectronicState):
    """
    A base section to define the Hubbard interactions of the system.
    """

    # TODO (@JosePizarro3 note): we need to have checks for when a `ModelSystem` is spin rotational invariant (then we only need to pass `u_interaction` and `j_hunds_coupling` and resolve the other quantities)

    n_orbitals = Quantity(
        type=np.int32,
        description="""
        Number of orbitals used to define the Hubbard interactions.
        """,
    )

    orbitals_ref = SubSection(
        sub_section=SectionProxy('ElectronicState'),
        repeats=True,
        description="""
        References to the `ElectronicState` sections that define the orbitals involved in
        Hubbard interactions. The ordering matches the rows/columns of `u_matrix`.
        Each reference can be a simple orbital (SphericalSymmetryState) or a more complex
        multi-orbital state, depending on the level of decomposition needed.
        """,
    )

    u_matrix = Quantity(
        type=np.float64,
        shape=['n_orbitals', 'n_orbitals'],
        unit='joule',
        description="""
        Value of the local Hubbard interaction matrix.
        The order of the rows and columns coincide with the elements in `orbitals_ref`.
        """,
    )

    u_interaction = Quantity(
        type=positive_float(),
        unit='joule',
        description="""
        Value of the (intra-orbital) Hubbard interaction
        """,
    )

    j_hunds_coupling = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Value of the (interorbital) Hund's coupling.
        """,
    )

    u_interorbital_interaction = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Value of the (interorbital) Coulomb interaction. In rotational invariant systems,
        u_interorbital_interaction = u_interaction - 2 * j_hunds_coupling.
        """,
    )

    j_local_exchange_interaction = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Value of the exchange interaction. In rotational invariant systems, j_local_exchange_interaction = j_hunds_coupling.
        """,
    )

    u_effective = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Value of the effective U parameter (u_interaction - j_local_exchange_interaction).
        """,
    )

    slater_integrals = Quantity(
        type=np.float64,
        shape=[3],
        unit='joule',
        description="""
        Value of the Slater integrals [F0, F2, F4] in spherical harmonics used to derive
        the local Hubbard interactions:

            u_interaction = ((2.0 / 7.0) ** 2) * (F0 + 5.0 * F2 + 9.0 * F4) / (4.0*np.pi)

            u_interorbital_interaction = ((2.0 / 7.0) ** 2) * (F0 - 5.0 * F2 + 3.0 * 0.5 * F4) / (4.0*np.pi)

            j_hunds_coupling = ((2.0 / 7.0) ** 2) * (5.0 * F2 + 15.0 * 0.25 * F4) / (4.0*np.pi)

        See e.g., Elbio Dagotto, Nanoscale Phase Separation and Colossal Magnetoresistance,
        Chapter 4, Springer Berlin (2003).
        """,
    )

    double_counting_correction = Quantity(
        type=str,
        description="""
        Name of the double counting correction algorithm applied.
        """,
    )

    @log
    def resolve_u_interactions(self) -> tuple | None:
        """
        Resolves the Hubbard interactions (u_interaction, u_interorbital_interaction, j_hunds_coupling)
        from the Slater integrals (F0, F2, F4) in the units defined for the Quantity.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[tuple]): The Hubbard interactions (u_interaction, u_interorbital_interaction, j_hunds_coupling).
        """
        logger = self.resolve_u_interactions.__annotations__['logger']
        if self.slater_integrals is None or len(self.slater_integrals) != 3:
            logger.warning(
                'Could not find `slater_integrals` or the length is not three.'
            )  # TODO: move shape-check to schema
            return None, None, None
        f0 = self.slater_integrals[0]
        f2 = self.slater_integrals[1]
        f4 = self.slater_integrals[2]
        u_interaction = ((2.0 / 7.0) ** 2) * (f0 + 5.0 * f2 + 9.0 * f4) / (4.0 * np.pi)
        u_interorbital_interaction = (
            ((2.0 / 7.0) ** 2) * (f0 - 5.0 * f2 + 3.0 * f4 / 2.0) / (4.0 * np.pi)
        )
        j_hunds_coupling = (
            ((2.0 / 7.0) ** 2) * (5.0 * f2 + 15.0 * f4 / 4.0) / (4.0 * np.pi)
        )
        return u_interaction, u_interorbital_interaction, j_hunds_coupling

    @log
    def resolve_u_effective(self) -> pint.Quantity | None:
        """
        Resolves the effective U parameter (u_interaction - j_local_exchange_interaction).

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[pint.Quantity]): The effective U parameter.
        """
        logger = self.resolve_u_effective.__annotations__['logger']
        if self.u_interaction is None:
            logger.warning('Could not find `HubbardInteractions.u_interaction`.')
            return None

        if self.j_local_exchange_interaction is None:
            self.j_local_exchange_interaction = 0.0 * ureg.eV

        return self.u_interaction - self.j_local_exchange_interaction

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Obtain (u, up, j_hunds_coupling) from slater_integrals
        if (
            self.u_interaction is None
            and self.u_interorbital_interaction is None
            and self.j_hunds_coupling is None
        ):
            (
                self.u_interaction,
                self.u_interorbital_interaction,
                self.j_hunds_coupling,
            ) = self.resolve_u_interactions(logger=logger)

        # If u_effective is not available, calculate it
        if self.u_effective is None:
            self.u_effective = self.resolve_u_effective(logger=logger)

        # Check if length of `orbitals_ref` is the same as the length of `u_matrix`:
        if self.u_matrix is not None and self.orbitals_ref is not None:
            if len(self.u_matrix) != len(
                self.orbitals_ref
            ):  # TODO: move shape-check to schema
                logger.error(
                    'The length of `HubbardInteractions.u_matrix` does not coincide with length of `HubbardInteractions.orbitals_ref`.'
                )


class ParticleState(Entity):
    """
    Generic base section representing the state of a particle in a simulation.
    This can be extended to include any common quantities in the future.
    """

    label = Quantity(
        type=str,
        description="""
        User- or program-package-defined identifier for this particle.
        """,
    )

    def get_label(self) -> str | None:
        """
        Returns the label of the particle.
        """
        return self.label


class AtomsState(ParticleState):
    """
    A base section to define each atom state information.
    """

    chemical_symbol = Quantity(
        type=MEnum(ase.data.chemical_symbols[1:]),
        description="""
        Symbol of the element, e.g. 'H', 'Pb'. This quantity is equivalent to `atomic_numbers`.
        """,
    )

    atomic_number = Quantity(
        type=np.int32,
        description="""
        Atomic number Z. This quantity is equivalent to `chemical_symbol`.
        """,
    )

    charge = Quantity(
        type=np.int32,
        default=0,
        description="""
        Charge of the atom. It is defined as the number of extra electrons or holes in the
        atom. If the atom is neutral, charge = 0 and the summation of all (if available) the`ElectronicState.occupation`
        coincides with the `atomic_number`. Otherwise, charge can be any positive integer (+1, +2...)
        for cations or any negative integer (-1, -2...) for anions.

        Note: for `CoreHole` systems we do not consider the charge of the atom even if
        we do not store the final `ElectronicState` where the electron was excited to.
        """,
    )

    spin = Quantity(
        type=np.int32,
        default=0,
        description="""
        Total spin quantum number, S.
        """,
    )

    label = Quantity(
        type=str,
        description="""
        User- or program-package-defined identifier for this atomic site.
        e.g. 'H1', 'H1a', 'C_eq'.
        It doesn't replace `chemical_symbol`, but merely gives users a more specialized token for the unique site name.
        """,
    )

    electronic_state = SubSection(sub_section=ElectronicState.m_def)

    @log
    def get_label(self) -> str | None:
        """
        Returns the label of the particle.
        """
        return self.chemical_symbol if self.chemical_symbol else self.label

    def resolve_chemical_symbol(self, logger: 'BoundLogger') -> str | None:
        """
        Resolves the `chemical_symbol` from the `atomic_number`.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[str]): The resolved `chemical_symbol`.
        """
        logger = self.resolve_chemical_symbol.__annotations__['logger']
        if self.atomic_number is not None:
            try:
                return ase.data.chemical_symbols[self.atomic_number]
            except IndexError:
                logger.error(
                    'The `AtomsState.atomic_number` is out of range of the periodic table.'
                )
        return None

    @log
    def resolve_atomic_number(self) -> int | None:
        """
        Resolves the `atomic_number` from the `chemical_symbol`.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[int]): The resolved `atomic_number`.
        """
        logger = self.resolve_atomic_number.__annotations__['logger']
        if self.chemical_symbol is not None:
            try:
                return ase.data.atomic_numbers[self.chemical_symbol]
            except IndexError:
                logger.error(
                    'The `AtomsState.chemical_symbol` is not recognized in the periodic table.'
                )
        return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.electronic_state:
            self.electronic_state.populate_atoms_state_refs(self)

        # Get chemical_symbol from atomic_number and viceversa
        if self.chemical_symbol is None:
            self.chemical_symbol = self.resolve_chemical_symbol(logger=logger)
        elif self.atomic_number is None:
            self.atomic_number = self.resolve_atomic_number(logger=logger)
        else:
            # If both are set, check if they match
            if self.atomic_number != ase.data.atomic_numbers[self.chemical_symbol]:
                logger.error(
                    'The `AtomsState.atomic_number` and `chemical_symbol` do not match.'
                )


class CGBeadState(ParticleState):
    """
    A section to define coarse-grained bead state information.
    """

    # ? What do we want to qualify as type identifier? What safety checks do we need?
    bead_symbol = Quantity(
        type=str,
        description="""
        Symbol(s) describing the (base) CG particle type. Equivalent to chemical_symbol
        for atomic elements.
        """,
    )

    label = Quantity(
        type=str,
        description="""
        User- or program-package-defined identifier for this bead site.
        This could be used to store primary FF labels in cases where only a
        secondary specification is required. Otherwise, `alt_labels` are
        used to document more complex bead identifiers, e.g., bead interactions based
        on connectivity.
        """,
    )

    alt_labels = Quantity(
        type=str,
        shape=['*'],
        description="""
        A list of bead labels for multifaceted bead characterization.
        """,
    )

    mass = Quantity(
        type=np.float64,
        unit='kg',
        description="""
        Total mass of the particle.
        """,
    )

    charge = Quantity(
        type=np.float64,
        unit='coulomb',
        description="""
        Total charge of the particle.
        """,
    )

    # Other possible quantities
    #     diameter: float
    #         The diameter of each particle.
    #         Default: 1.0
    #     body: int
    #         The composite body associated with each particle. The value -1
    #         indicates no body.
    #         Default: -1
    #     moment_inertia: float
    #         The moment_inertia of each particle (I_xx, I_yy, I_zz).
    #         This inertia tensor is diagonal in the body frame of the particle.
    #         The default value is for point particles.
    #         Default: 0, 0, 0
    #     scaled_positions: list of scaled-positions #! for cell if relevant
    #         Like positions, but given in units of the unit cell.
    #         Can not be set at the same time as positions.
    #         Default: 0, 0, 0
    #     orientation: float
    #         The orientation of each particle. In scalar + vector notation,
    #         this is (r, a_x, a_y, a_z), where the quaternion is q = r + a_xi + a_yj + a_zk.
    #         A unit quaternion has the property: sqrt(r^2 + a_x^2 + a_y^2 + a_z^2) = 1.
    #         Default: 0, 0, 0, 0
    #     angmom: float #? for cell or here?
    #         The angular momentum of each particle as a quaternion.
    #         Default: 0, 0, 0, 0
    #     image: int #! advance PBC stuff would go in cell I guess
    #         The number of times each particle has wrapped around the box (i_x, i_y, i_z).
    #         Default: 0, 0, 0

    def get_label(self) -> str | None:
        """
        Returns the label of the particle.
        """
        symbol = self.bead_symbol if self.bead_symbol else self.label
        if not symbol:
            alts = self.alt_labels
            symbol = alts[0] if alts else None

        return symbol

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
