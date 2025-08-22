from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import numpy as np
from nomad.config import config
from nomad.datamodel.data import Schema
from nomad.datamodel.metainfo.basesections import Activity, Entity
from nomad.metainfo import Datetime, Quantity, SchemaPackage, Section, SubSection

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    CGBeadState,
    ParticleState,
)
from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.utils import get_composition, log

from .common import Time

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)

m_package = SchemaPackage()


def set_not_normalized(func: 'Callable'):
    """
    Decorator to set the section as not normalized.
    Typically decorates the section initializer.
    """

    def wrapper(self, *args, **kwargs) -> None:
        func(self, *args, **kwargs)
        self._is_normalized = False

    return wrapper


def check_normalized(func: 'Callable'):
    """
    Decorator to check if the section is already normalized.
    Typically decorates the section normalizer.
    """

    def wrapper(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        if self._is_normalized:
            return None
        func(self, archive, logger)
        self._is_normalized = True

    return wrapper


class Program(Entity):
    """
    A base section used to specify a well-defined program used for computation.

    Synonyms:
     - code
     - software
    """

    name = Quantity(
        type=str,
        description="""
        The name of the program.
        """,
    )

    version = Quantity(
        type=str,
        description="""
        The version label of the program.
        """,
    )

    link = Quantity(
        type=str,
        description="""
        Website link to the program in published information.
        """,
    )

    version_internal = Quantity(
        type=str,
        description="""
        Specifies a program version tag used internally for development purposes.
        Any kind of tagging system is supported, including git commit hashes.
        """,
    )

    subroutine_name_internal = Quantity(
        type=str,
        description="""
        Specifies the name of the subroutine of the program at large.
        This only applies when the routine produced (almost) all of the output,
        so the naming is representative. This naming is mostly meant for users
        who are familiar with the program's structure.
        """,
    )

    compilation_host = Quantity(
        type=str,
        description="""
        Specifies the host on which the program was compiled.
        """,
    )


class BaseSimulation(Activity, Time):
    """
    A computational simulation that produces output data from a given input model system
    and input methodological parameters.

    Synonyms:
        - computation
        - calculation
    """

    m_def = Section(
        links=['https://liusemweb.github.io/mdo/core/1.1/index.html#Calculation']
    )

    datetime_end = Quantity(
        type=Datetime,
        description="""
        The date and time when this computation ended.
        """,
    )

    cpu1_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The starting time of the computation on the (first) CPU 1.
        """,
    )

    cpu1_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The end time of the computation on the (first) CPU 1.
        """,
    )

    wall_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the starting of the computation.
        """,
    )

    wall_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the end of the computation.
        """,
    )

    program = SubSection(sub_section=Program.m_def, repeats=False)


class Simulation(BaseSimulation, Schema):
    """
    A `Simulation` is a computational calculation that produces output data from a given input model system
    and input (model) methodological parameters. The output properties obtained from the simulation are stored
    in a list under `outputs`.

    Each sub-section of `Simulation` is defined in their corresponding modules: `model_system.py`, `model_method.py`,
    and `outputs.py`.

    The basic entry data for a `Simulation`, known as `SinglePoint` workflow, contains all the self-consistent (SCF) steps
    performed to converge the calculation, i.e., we do not split each SCF step in its own entry but rather group them in a general one.

    Synonyms:
        - calculation
        - computation
    """

    representative_system_index = Quantity(
        type=np.int32,
        description="""
        The index of the "representative system" in the `model_system` list.
        """,
    )

    model_system = SubSection(sub_section=ModelSystem.m_def, repeats=True)

    model_method = SubSection(sub_section=ModelMethod.m_def, repeats=True)

    outputs = SubSection(sub_section=Outputs.m_def, repeats=True)

    def _set_system_branch_depth(
        self, system_parent: ModelSystem, branch_depth: int = 0
    ):
        for system_child in system_parent.sub_systems:
            system_child.branch_depth = branch_depth + 1
            self._set_system_branch_depth(
                system_parent=system_child, branch_depth=branch_depth + 1
            )

    @staticmethod
    def get_composition_formula(system: ModelSystem) -> str | None:
        # Honor custom formulas
        if system.composition_formula is not None:
            return system.composition_formula

        formula = None
        subsystems = system.sub_systems
        # INTERNAL NODE: use child branch labels
        if subsystems:
            children_names = [(child.branch_label or 'Unknown') for child in subsystems]
            children_names = (
                children_names
                if not all([name == 'Unknown' for name in children_names])
                else []
            )
            formula = get_composition(children_names=children_names)

        # LEAF NODE or all children have no branch_label
        if not formula:
            if system.particle_indices is None and not system.is_root_system():
                return None

            names = (
                system.get_symbols()
            )  # already slices from root via particle_indices
            formula = get_composition(children_names=names) if names else None

        return formula

    @staticmethod
    def set_composition_formula(system_parent: ModelSystem) -> None:
        """
        Determine and set the composition_formula for `system_parent` and all descendants.

        Rules
        -----
        - Never overwrite a pre-set custom composition_formula (only set when None).
        - Internal nodes (with children):
            * Formula counts child branch labels when available, using 'Unknown' otherwise.
            * If no children have branch labels, falls back to using particle labels.
        - Leaves (no children):
            * Uses particle labels.
            * If particle_indices or symbols are missing → leave as None.

        Args:
        ----
            system_parent (ModelSystem): The upper-most level of the system hierarchy to consider.

        """
        system_parent.composition_formula = Simulation.get_composition_formula(
            system_parent
        )
        for child in system_parent.sub_systems:
            Simulation.set_composition_formula(system_parent=child)

    @log
    def _validate_and_set_representative_system(self) -> None:
        """
        Ensure exactly one representative `ModelSystem` exists in `self.model_system`,
        and update `self.representative_system_index` to point to it.

        Behavior
        --------
        - **Zero representatives:** Mark the *last* item in `self.model_system` as
        representative and set `self.representative_system_index = -1`
        (Python’s negative index for the last element).
        - **Multiple representatives:** Log a warning, demote all, then keep the
        *last* representative encountered. Store its (non-negative) index in
        `self.representative_system_index`.
        - **Exactly one representative:** Leave flags as is and set
        `self.representative_system_index` to that item’s index.

        Side Effects
        ------------
        - Mutates `is_representative` on elements of `self.model_system`.
        - Sets `self.representative_system_index`.
        - Emits a warning if multiple representatives are found.

        Requirements / Notes
        --------------------
        - Assumes `self.model_system` is **non-empty**. If it can be empty in your
        context, guard against `IndexError` before calling or extend this method
        to handle the empty case explicitly.
        - In case of multiple or no representatives, the last one in the list is taken
        since it is common that the list of model systems links to some serial workflow,
        e.g., Geometry Optimization or Molecular Dynamics.
        - Runs in O(n) over the number of systems.

        Returns
        -------
        None
        """
        # TODO consider adding programmatic enforcement of model_system natural ordering
        logger = self._validate_and_set_representative_system.__annotations__['logger']

        if not self.model_system:
            logger.error('No system information reported.')
            return

        # indices of representative systems
        rep_idx = [i for i, ms in enumerate(self.model_system) if ms.is_representative]

        if len(rep_idx) == 0:
            self.model_system[-1].is_representative = True
            self.representative_system_index = -1
        elif len(rep_idx) > 1:
            logger.warning(
                'Multiple representative systems found, one allowed.'
                ' Will use the last `ModelSystem` found.'
            )
            for idx in rep_idx:
                self.model_system[idx].is_representative = False
            self.model_system[rep_idx[-1]].is_representative = True
            self.representative_system_index = rep_idx[-1]
        else:  ## len(rep_idx) == 1
            self.representative_system_index = rep_idx[0]

    # TODO enumerate normalization steps relevant to rep system in docstring
    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """

        Normalize the `Simulation` section:
        - Validate and set the representative system.
            - Certain normalization steps are only applied to the representative system to avoid redundancy.
            - The representative system is used to power some downstream tools.
            - The representative system should be the primary source of information for the user.

        Args:
            archive (EntryArchive): _description_
            logger (BoundLogger): _description_
        """
        super(Schema, self).normalize(archive, logger)

        # Validate that there is exactly one representative system and set the index
        self._validate_and_set_representative_system()

        # Setting up the `branch_depth` in the parent-child tree
        for system_parent in self.model_system:
            _ = system_parent.get_root_system()  # ensure no cycles in the tree
            system_parent.branch_depth = 0
            self.set_composition_formula(system_parent=system_parent)
            if len(system_parent.sub_systems) == 0:
                continue
            self._set_system_branch_depth(system_parent=system_parent)


m_package.__init_metainfo__()
