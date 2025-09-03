from typing import TYPE_CHECKING, Any, Optional, Union

import ase
import numpy as np
import pint
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.basesections.v2 import Entity
from nomad.metainfo import MEnum, Quantity, SubSection
from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import RussellSaundersState, log

# TODO rename this file particles_state.py or place ParticleState in model_system.py
# TODO and make separate module files for AtomsState, CGBeadState, etc.


class OrbitalsState(Entity):
    """
    A base section used to define the orbital state of an atom.
    """

    # TODO add check for `j_quantum_number` and `mj_quantum_number`
    # TODO: add the relativistic kappa_quantum_number

    n_quantum_number = Quantity(
        type=np.int32,
        description="""
        Principal quantum number of the orbital state.
        """,
    )

    l_quantum_number = Quantity(
        type=np.int32,
        description="""
        Azimuthal quantum number of the orbital state. This quantity is equivalent to `l_quantum_symbol`.
        """,
    )

    l_quantum_symbol = Quantity(
        type=str,
        description="""
        Azimuthal quantum symbol of the orbital state, "s", "p", "d", "f", etc. This
        quantity is equivalent to `l_quantum_number`.
        """,
    )

    ml_quantum_number = Quantity(
        type=np.int32,
        description="""
        Azimuthal projection number of the `l` vector. This quantity is equivalent to `ml_quantum_symbol`.
        """,
    )

    ml_quantum_symbol = Quantity(
        type=str,
        description="""
        Azimuthal projection symbol of the `l` vector, "x", "y", "z", etc. This quantity is equivalent
        to `ml_quantum_number`.
        """,
    )

    j_quantum_number = Quantity(
        type=np.float64,
        shape=['1..2'],
        description="""
        Total angular momentum quantum number $j = |l-s| ... l+s$. Necessary with strong
        L-S coupling or non-collinear spin systems.
        """,
    )

    mj_quantum_number = Quantity(
        type=np.float64,
        shape=['*'],
        description="""
        Azimuthal projection of the `j` vector. Necessary with strong L-S coupling or
        non-collinear spin systems.
        """,
    )

    ms_quantum_number = Quantity(
        type=np.float64,
        description="""
        Spin quantum number. Set to -1 for spin down and +1 for spin up. In non-collinear spin
        systems, the projection axis $z$ should also be defined.
        """,
    )

    ms_quantum_symbol = Quantity(
        type=MEnum('down', 'up'),
        description="""
        Spin quantum symbol. Set to 'down' for spin down and 'up' for spin up. In non-collinear
        spin systems, the projection axis $z$ should also be defined.
        """,
    )

    degeneracy = Quantity(
        type=np.int32,
        description="""
        The degeneracy of the orbital state. The degeneracy is the number of states with the same
        energy. It is equal to 2 * l + 1 for non-relativistic systems and 2 * j + 1 for
        relativistic systems, if ms_quantum_number is defined (otherwise a factor of 2 is included).
        """,
    )

    occupation = Quantity(
        type=np.float64,
        description="""
        The number of electrons in the orbital state. The state is fully occupied if
        occupation = degeneracy.
        """,
    )

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
            'ms_symbols': dict(zip((-0.5, 0.5), ('down', 'up'))),
            'l_numbers': {v: k for k, v in self._orbitals[-1].items()},
            'ml_numbers': {
                k: {v: k for k, v in self._orbitals[k].items()} for k in range(4)
            },
            'ms_numbers': dict(zip(('down', 'up'), (-0.5, 0.5))),
        }

    @log
    def validate_quantum_numbers(self) -> bool:
        """
        Validate the quantum numbers (`n`, `l`, `ml`, `ms`) by checking if they are physically sensible.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (bool): True if the quantum numbers are physically sensible, False otherwise.
        """
        logger = self.validate_quantum_numbers.__annotations__['logger']
        if self.n_quantum_number is not None and self.n_quantum_number < 1:
            logger.error('The `n_quantum_number` must be greater than 0.')
            return False
        if self.l_quantum_number is not None and self.l_quantum_number < 0:
            logger.error('The `l_quantum_number` must be >= 0.')
            return False
        if self.ml_quantum_number is not None and (
            self.ml_quantum_number < -self.l_quantum_number
            or self.ml_quantum_number > self.l_quantum_number
        ):
            logger.error(
                'The `ml_quantum_number` must be between `-l_quantum_number` and `l_quantum_number`.'
            )
            return False
        if self.ms_quantum_number is not None and self.ms_quantum_number not in [
            -0.5,
            0.5,
        ]:
            logger.error('The `ms_quantum_number` must be -0.5 or 0.5.')
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
            quantum_name (str): The quantum name to resolve. Can be 'l', 'ml' or 'ms'.
            quantum_type (str): The type of the quantum name. Can be 'number' or 'symbol'.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[Union[str, int]]): The quantum number or symbol resolved from the orbitals_map.
        """
        if quantum_name not in ['l', 'ml', 'ms']:
            logger.warning("The quantum_name is not recognized. Try 'l', 'ml' or 'ms'.")
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
        if quantum_name in ['l', 'ms']:
            quantity = orbital_quantity.get(other_quantity)
        elif quantum_name == 'ml':
            if self.l_quantum_number is None:
                return None
            quantity = orbital_quantity.get(self.l_quantum_number, {}).get(
                other_quantity
            )
        return quantity

    def resolve_degeneracy(self) -> int | None:
        """
        Resolves the degeneracy of the orbital state. If `j_quantum_number` is not defined, then the
        degeneracy is computed from the `l_quantum_number` and `ml_quantum_number`. If `j_quantum_number`
        is defined, then the degeneracy is computed from the `j_quantum_number` and `mj_quantum_number`.
        There is a factor of 2 included if `ms_quantum_number` is not defined (for orbitals which
        are spin-degenerated).

        Returns:
            (Optional[int]): The degeneracy of the orbital state.
        """
        degeneracy = None
        if (
            self.l_quantum_number
            and self.ml_quantum_number is None
            and self.j_quantum_number is None
        ):
            if self.ms_quantum_number:
                degeneracy = 2 * self.l_quantum_number + 1
            else:
                degeneracy = 2 * (2 * self.l_quantum_number + 1)
        elif (
            self.l_quantum_number
            and self.ml_quantum_number
            and self.j_quantum_number is None
        ):
            if self.ms_quantum_number:
                degeneracy = 1
            else:
                degeneracy = 2
        elif self.j_quantum_number is not None:
            degeneracy = 0
            for jj in self.j_quantum_number:
                if self.mj_quantum_number is not None:
                    mjs = RussellSaundersState.generate_MJs(
                        J=self.j_quantum_number[0], rising=True
                    )
                    degeneracy += len(
                        [mj for mj in mjs if mj in self.mj_quantum_number]
                    )
                else:
                    degeneracy += RussellSaundersState(J=jj, occ=1).degeneracy
        return degeneracy

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # General checks for physical quantum numbers and symbols
        if not self.validate_quantum_numbers(logger=logger):
            logger.error('The quantum numbers are not physical.')
            return

        # Resolving the quantum numbers and symbols if not available
        for quantum_name in ['l', 'ml', 'ms']:
            for quantum_type in ['number', 'symbol']:
                quantity = self.resolve_number_and_symbol(
                    quantum_name=quantum_name, quantum_type=quantum_type, logger=logger
                )
                if getattr(self, f'{quantum_name}_quantum_{quantum_type}') is None:
                    setattr(self, f'{quantum_name}_quantum_{quantum_type}', quantity)

        # Resolve the degeneracy
        if self.degeneracy is None:
            self.degeneracy = self.resolve_degeneracy()


class CoreHole(ArchiveSection):
    """
    A base section used to define the core-hole state of an atom by referencing the `OrbitalsState`
    section where the core-hole was generated.
    """

    orbital_ref = Quantity(
        type=OrbitalsState,
        description="""
        Reference to the OrbitalsState section that is used as a basis to obtain the `CoreHole` section.
        """,
    )

    n_excited_electrons = Quantity(
        type=np.float64,
        description="""
        The electron charge excited for modelling purposes. This is a number between 0 and 1 (Janak state).
        If `dscf_state` is set to 'initial', then this quantity is set to None (but assumed to be excited
        to an excited state).
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
    def resolve_occupation(self) -> np.float64 | None:
        """
        Resolves the occupation of the orbital state. The occupation is resolved from the degeneracy
        and the number of excited electrons.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[np.float64]): The occupation of the active orbital state.
        """
        logger = self.resolve_occupation.__annotations__['logger']
        if self.orbital_ref is None or self.n_excited_electrons is None:
            logger.warning(
                'Cannot resolve occupation without `orbital_ref` or `n_excited_electrons`.'
            )
            return None
        if self.orbital_ref.occupation is None:
            degeneracy = self.orbital_ref.resolve_degeneracy()
            if degeneracy is None:
                logger.warning('Cannot resolve occupation without `degeneracy`.')
                return None
            return degeneracy - self.n_excited_electrons
        return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Check if n_excited_electrons is between 0 and 1
        if self.n_excited_electrons < 0 or self.n_excited_electrons > 1:
            logger.error('Number of excited electrons must be between 0 and 1.')
            return

        # Resolve the occupation of the active orbital state
        if self.orbital_ref is not None:
            # If dscf_state is 'initial', then n_excited_electrons is set to 0
            if self.dscf_state == 'initial':
                self.n_excited_electrons = None
                self.orbital_ref.degeneracy = 1
            if self.orbital_ref.occupation is None:
                self.orbital_ref.occupation = self.resolve_occupation(logger=logger)


class HubbardInteractions(ArchiveSection):
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

    orbitals_ref = Quantity(
        type=OrbitalsState,
        shape=['n_orbitals'],
        description="""
        Reference to the `OrbitalsState` sections that are used as a basis to obtain the Hubbard
        interaction matrices.
        """,
    )

    u_matrix = Quantity(
        type=np.float64,
        shape=['n_orbitals', 'n_orbitals'],
        unit='joule',
        description="""
        Value of the local Hubbard interaction matrix. The order of the rows and columns coincide
        with the elements in `orbital_ref`.
        """,
    )

    u_interaction = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Value of the (intraorbital) Hubbard interaction
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
            )
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
        if self.u_interaction.magnitude < 0.0:
            logger.error('The `HubbardInteractions.u_interaction` must be positive.')
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

        # Check if length of `orbitals_ref` is the same as the length of `umn`:
        if self.u_matrix is not None and self.orbitals_ref is not None:
            if len(self.u_matrix) != len(self.orbitals_ref):
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

    def get_label(self) -> str:
        """
        Returns the label of the particle.
        """
        return self.label

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


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
        atom. If the atom is neutral, charge = 0 and the summation of all (if available) the`OrbitalsState.occupation`
        coincides with the `atomic_number`. Otherwise, charge can be any positive integer (+1, +2...)
        for cations or any negative integer (-1, -2...) for anions.

        Note: for `CoreHole` systems we do not consider the charge of the atom even if
        we do not store the final `OrbitalsState` where the electron was excited to.
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

    orbitals_state = SubSection(sub_section=OrbitalsState.m_def, repeats=True)

    core_hole = SubSection(sub_section=CoreHole.m_def, repeats=False)

    hubbard_interactions = SubSection(
        sub_section=HubbardInteractions.m_def, repeats=False
    )

    @log
    def get_label(self) -> str:
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

    def get_label(self) -> str:
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
