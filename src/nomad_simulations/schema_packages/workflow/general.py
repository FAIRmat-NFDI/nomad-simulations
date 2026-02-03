from collections.abc import Iterable

import jmespath
import numpy as np
from nomad.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task, TaskReference, Workflow
from nomad.metainfo import Datetime, MEnum, Quantity, SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.common import SimulationTime
from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties import ElectronicDensityOfStates
from nomad_simulations.schema_packages.utils import log
from nomad_simulations.schema_packages.workflow.trajectory import (
    FreeEnergyCalculations,
    Pressures,
    RadiiOfGyration,
    Temperatures,
)

# TODO make this a function to check required number of tasks
INCORRECT_N_TASKS = 'Incorrect number of tasks found.'

m_package = SchemaPackage()


class SimulationTask(Task):
    pass


class WorkflowConvergenceTarget(ArchiveSection):
    """
    Abstract base class for defining convergence targets.

    Following the PhysicalProperty pattern, this provides a common interface for
    all convergence criteria. Child classes define specific physical properties
    (e.g., energy, force) with proper units. The base class handles all convergence
    checking logic based on the convergence_type enum.
    """

    threshold = Quantity(
        type=np.float64,
        description="""
        Threshold value for convergence. Units are defined in child classes.
        """,
    )

    convergence_type = Quantity(
        type=MEnum('absolute', 'relative', 'maximum', 'rms', 'residuum'),
        description="""
        Specifies how convergence is evaluated:

        | Type | Description |
        | ---- | ----------- |
        | `'absolute'` | Absolute difference between iterations: \|X_n - X_{n-1}\| < threshold |
        | `'relative'` | Relative difference: \|X_n - X_{n-1}\|/\|X_n\| < threshold |
        | `'maximum'` | Maximum component difference: max\|X_i,n - X_i,{n-1}\| < threshold |
        | `'rms'` | Root mean square: sqrt(Σ\|X_i,n - X_i,{n-1}\|²/N) < threshold |
        | `'residuum'` | Difference from initial estimate at step start |
        """,
    )

    is_reached = Quantity(
        type=bool,
        description="""
        Indicates whether the convergence criterion was met (True) or not (False).
        """,
    )

    def _get_convergence_value(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> float | np.ndarray | None:
        """
        Extract the value to check for convergence from the archive.
        Child classes must override this to return the appropriate value.
        
        Returns:
            The value to check (should already be converted to appropriate units),
            or None if the value cannot be determined.
        """
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement _get_convergence_value()'
        )

    def _check_absolute(self, value: float) -> bool:
        """Check absolute convergence: |value| < threshold"""
        if self.threshold is None:
            return False
        return abs(value) < self.threshold

    def _check_relative(self, value: float, reference: float) -> bool:
        """Check relative convergence: |value|/|reference| < threshold"""
        if self.threshold is None or abs(reference) < 1e-15:
            return False
        return abs(value / reference) < self.threshold

    def _check_maximum(self, values: np.ndarray) -> bool:
        """Check maximum convergence: max(|values|) < threshold"""
        if self.threshold is None:
            return False
        return np.max(np.abs(values)) < self.threshold

    def _check_rms(self, values: np.ndarray) -> bool:
        """Check RMS convergence: sqrt(mean(values²)) < threshold"""
        if self.threshold is None:
            return False
        return np.sqrt(np.mean(values**2)) < self.threshold

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Check convergence by comparing current value against threshold.
        Uses the convergence_type to determine the comparison method.
        """
        if not archive.data:
            return

        try:
            value = self._get_convergence_value(archive, logger)
            if value is None:
                return

            conv_type = self.convergence_type or 'absolute'

            # Handle scalar vs array values
            if isinstance(value, int | float | np.floating):
                # Scalar value - use absolute or relative
                if conv_type == 'absolute':
                    self.is_reached = self._check_absolute(value)
                elif conv_type == 'relative':
                    # For relative, child class should provide reference
                    logger.warning(
                        f'Relative convergence requires reference value in '
                        f'{self.__class__.__name__}'
                    )
                else:
                    self.is_reached = self._check_absolute(value)
            
            elif isinstance(value, np.ndarray):
                # Array value - can use maximum or rms
                if conv_type == 'maximum':
                    self.is_reached = self._check_maximum(value)
                elif conv_type == 'rms':
                    self.is_reached = self._check_rms(value)
                elif conv_type == 'absolute':
                    # For array, treat as maximum
                    self.is_reached = self._check_maximum(value)
                else:
                    self.is_reached = self._check_maximum(value)

        except Exception as e:
            logger.debug(
                f'Could not check convergence for {self.__class__.__name__}: {e}'
            )


class EnergyConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for energy in SCF or optimization workflows.
    The convergence_type determines how energy convergence is evaluated.
    """

    threshold = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Energy convergence threshold.
        """,
    )

    def _get_convergence_value(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> float | None:
        """Extract energy convergence value from archive."""
        try:
            # Try to get SCF energy difference (most common case)
            delta_energy = archive.data.outputs[-1].scf_steps[-1].delta_energies_total
            if delta_energy is not None:
                return delta_energy.to('joule').magnitude
        except (AttributeError, IndexError, TypeError):
            logger.debug('Could not extract energy convergence value from outputs.')
        return None


class ForceConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for forces in optimization or SCF workflows.
    The convergence_type determines how force convergence is evaluated.
    """

    threshold = Quantity(
        type=np.float64,
        unit='newton',
        description="""
        Force convergence threshold.
        """,
    )

    def _get_convergence_value(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> float | np.ndarray | None:
        """Extract force convergence value from archive."""
        try:
            conv_type = self.convergence_type or 'maximum'
            
            # For maximum force in geometry optimization, check workflow level
            if conv_type == 'maximum' and hasattr(archive, 'workflow2') and archive.workflow2:
                final_force_max = archive.workflow2.results.final_force_maximum
                if final_force_max is not None:
                    return final_force_max.to('newton').magnitude
            
            # For absolute (SCF force delta)
            if conv_type == 'absolute' and archive.data.outputs:
                delta_force = archive.data.outputs[-1].scf_steps[-1].delta_force_abs
                if delta_force is not None:
                    return delta_force.to('newton').magnitude
            
            # Fallback: get force array from last output
            if archive.data.outputs:
                forces = archive.data.outputs[-1].total_forces
                if forces is not None and len(forces) > 0:
                    # Return force magnitudes for each atom
                    force_magnitudes = np.linalg.norm(forces[-1].value, axis=1)
                    return force_magnitudes
        except (AttributeError, IndexError, TypeError):
            logger.debug('Could not extract force convergence value from outputs.')
        return None


class PotentialConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for potential in SCF workflows.
    The convergence_type determines how potential convergence is evaluated.
    """

    threshold = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Potential convergence threshold.
        """,
    )

    def _get_convergence_value(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> float | None:
        """Extract potential convergence value from archive."""
        try:
            # Most common: RMS potential difference
            delta_potential = archive.data.outputs[-1].scf_steps[-1].delta_potential_rms
            if delta_potential is not None:
                return delta_potential.to('joule').magnitude
        except (AttributeError, IndexError, TypeError):
            logger.debug('Could not extract potential convergence value from outputs.')
        return None


class ChargeConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for charge/electron density in SCF workflows.
    The convergence_type determines how density convergence is evaluated.
    """

    threshold = Quantity(
        type=np.float64,
        description="""
        Charge/density convergence threshold (typically dimensionless or in electrons).
        """,
    )

    def _get_convergence_value(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> float | None:
        """Extract charge/density convergence value from archive."""
        try:
            delta_density = archive.data.outputs[-1].scf_steps[-1].delta_density_rms
            if delta_density is not None:
                # delta_density_rms is typically dimensionless or in electrons
                return float(delta_density) if not isinstance(delta_density, int | float) else delta_density
        except (AttributeError, IndexError, TypeError):
            logger.debug('Could not extract charge convergence value from outputs.')
        return None


class SimulationWorkflowMethod(ArchiveSection):
    """
    Base class for simulation workflow model sub-section definition.
    """

    _label = 'Input model'

    initial_system = Quantity(
        type=ModelSystem,
        description="""
        Reference to the input model_system.
        """,
    )

    initial_method = Quantity(
        type=ModelMethod,
        description="""
        Reference to the input model_method.
        """,
    )

    convergence_targets = SubSection(sub_section=WorkflowConvergenceTarget.m_def, repeats=True)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not archive.data:
            return

        # set references to initial system and method
        if not self.initial_system and archive.data.model_system:
            self.initial_system = archive.data.model_system[0]
        if not self.initial_method and archive.data.model_method:
            self.initial_method = archive.data.model_method[0]


# TODO: Is this nomad_simulations.common.SimulationTime ?
class WorkflowTime(ArchiveSection):
    """
    Contains time-related quantities.
    """

    datetime_end = Quantity(
        type=Datetime,
        description="""
        The date and time when the workflow ended.
        """,
    )

    cpu1_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The starting time of the workflow on the (first) CPU 1.
        """,
    )

    cpu1_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The end time of the workflow on the (first) CPU 1.
        """,
    )

    wall_start = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the starting of the workflow.
        """,
    )

    wall_end = Quantity(
        type=np.float64,
        unit='second',
        description="""
        The internal wall-clock time from the end of the workflow.
        """,
    )


class SimulationWorkflowResults(WorkflowTime):
    """
    Base class for simulation workflow results sub-section definition.
    """

    _label = 'Workflow results'

    finished_normally = Quantity(
        type=bool,
        shape=[],
        description="""
        Indicates if calculation terminated normally.
        """,
    )

    is_converged = Quantity(
        type=bool,
        description="""
        Represents if the convergence targets have been reached (True) or not (False).
        """,
    )

    convergence_targets = SubSection(sub_section=WorkflowConvergenceTarget.m_def, repeats=True)


class SimulationTaskReference(TaskReference, SimulationTask):
    pass


class SimulationWorkflow(Workflow, SimulationTask):
    """
    Base class for simulation workflows.

    It contains sub-sections model and results which are included in inputs and
    outputs, respectively.
    """

    _task_label = 'Task'

    method = SubSection(sub_section=SimulationWorkflowMethod.m_def)

    results = SubSection(sub_section=SimulationWorkflowResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = SimulationWorkflowMethod()

        if self.method in [inp.section for inp in self.inputs]:
            return

        logger = self.map_inputs.__annotations__['logger']
        self.method.normalize(archive, logger)
        # add method to inputs
        self.inputs.append(Link(name=self.method._label, section=self.method))

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = SimulationWorkflowResults()

        if self.results in [out.section for out in self.outputs]:
            return

        logger = self.map_outputs.__annotations__['logger']
        self.results.normalize(archive, logger)
        # add results to outputs
        self.outputs.append(Link(name=self.results._label, section=self.results))

    @log
    def map_tasks(self, archive: EntryArchive) -> None:
        """
        Generate tasks from archive data outputs. Tasks are ordered and linked based
        on the execution time of the calculation corresponding to the output.
        """
        # do not overwrite assigned tasks
        if self.tasks:
            return

        if not archive.data or not archive.data.outputs:
            return

        # do not overwrite if tasks are set but give out a warning that it maybe
        # inconsistent with the outputs
        logger = self.map_tasks.__annotations__['logger']
        if self.tasks:
            logger.warning('Tasks are predefined and will not generate from outputs.')
            return

        outputs = list(archive.data.outputs)
        outputs.sort(key=lambda x: x.wall_start or 0)
        tasks = []
        parent_n = 0
        root_n = 0
        for n, output in enumerate(outputs):
            task = SimulationTask(
                name=f'{self._task_label} {n}',
                outputs=[Link(name='Outputs', section=output)],
            )
            tasks.append(task)
            tstart = output.wall_start
            tend = outputs[parent_n].wall_end
            if tstart is None and tend is None:
                continue
            if tstart >= tend:
                task.inputs.extend(
                    [Link(name='Linked task', section=t) for t in tasks[parent_n:n]]
                )
                root_n = parent_n
                parent_n = n
            elif n != parent_n:
                task.inputs.extend(
                    [
                        Link(name='Linked task', section=t)
                        for t in tasks[root_n:parent_n]
                    ]
                )

        self.tasks.extend(tasks)

    @log
    def map_convergence(self, archive: EntryArchive) -> None:
        """
        Normalize convergence targets and determine overall convergence status.
        """
        if not archive.data or not archive.data.outputs:
            return
        logger = self.map_convergence.__annotations__['logger']

        # Get convergence targets from method
        convergence_targets = self.method.get('convergence_targets')
        if not convergence_targets:
            return

        # Normalize each convergence target (triggers convergence checks)
        for target in convergence_targets:
            target.normalize(archive, logger)

        # Copy normalized targets to results for visibility
        if not self.results.convergence_targets:
            self.results.convergence_targets = convergence_targets

        # Determine overall convergence status
        all_reached = all(target.is_reached for target in convergence_targets if target.is_reached is not None)
        any_checked = any(target.is_reached is not None for target in convergence_targets)
        
        if any_checked:
            if self.results.get('is_converged') is None:
                self.results.is_converged = all_reached
            elif self.results.is_converged != all_reached:
                logger.warning(
                    f'Derived convergence ({all_reached}) differs from parsed convergence '
                    f'({self.results.is_converged}).'
                )

    def normalize(self, archive: EntryArchive, logger: BoundLogger):
        """
        Link tasks based on start and end times.
        """
        if not self.name:
            self.name: str = self.m_def.name

        self.map_inputs(archive, logger=logger)

        self.map_outputs(archive, logger=logger)

        self.map_tasks(archive, logger=logger)

        self.map_convergence(archive, logger=logger)

    def _resolve_convergence_for_output(
        self,
        archive: EntryArchive,
        convergence_targets: list[WorkflowConvergenceTarget],
        logger: BoundLogger,
        output_index: int = -1,
    ) -> list[WorkflowConvergenceTarget]:
        """
        Helper method to resolve convergence targets for a specific output index.
        Used primarily for multi-step workflows like geometry optimization.
        
        Creates temporary copies of convergence targets and normalizes them
        against a specific output step.
        """
        resolved_targets = []
        
        for target in convergence_targets:
            # Create a copy of the target to avoid modifying the original
            target_copy = target.m_copy(deep=True)
            
            # For multi-output scenarios, we may need to adjust the archive context
            # This is a simplified approach - child classes can override for more complex logic
            target_copy.normalize(archive, logger)
            
            resolved_targets.append(target_copy)
        
        return resolved_targets


class SerialWorkflowResults(SimulationWorkflowResults):
    temperatures = SubSection(sub_section=Temperatures.m_def, repeats=True)

    pressures = SubSection(sub_section=Pressures.m_def, repeats=True)

    radii_of_gyration = SubSection(sub_section=RadiiOfGyration.m_def, repeats=True)

    free_energy_calculations = SubSection(
        sub_section=FreeEnergyCalculations.m_def, repeats=True
    )


class SerialWorkflow(SimulationWorkflow):
    """
    Base class for workflows where tasks are executed sequentially.
    """

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = SerialWorkflowResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if not self.tasks:
            logger.error(INCORRECT_N_TASKS)
            return

        # link tasks sequentially
        for n, task in enumerate(self.tasks):
            if task.inputs:
                continue
            if n == 0:
                inputs = self.inputs
            else:
                previous_task = self.tasks[n - 1]
                inputs = [
                    Link(
                        name='Linked task',
                        section=previous_task.task
                        if isinstance(previous_task, TaskReference)
                        else previous_task,
                    )
                ]

            task.inputs.extend([inp for inp in inputs if inp not in task.inputs])

        # add outputs of last task to outputs
        self.outputs.extend(
            [out for out in self.tasks[-1].outputs if out not in self.outputs]
        )


class ParallelWorkflow(SimulationWorkflow):
    """
    Base class for workflows where tasks are executed concurrently.
    """

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger=logger)

        if not self.tasks:
            logger.error(INCORRECT_N_TASKS)
            return

        for task in self.tasks:
            if not task.inputs:
                # link inputs to all tasks
                task.inputs.extend(self.inputs)

                # link tasks outputs to outputs
                self.outputs.extend(
                    [out for out in task.outputs if out not in self.outputs]
                )


# TODO @all: Does this belong here?
class ElectronicStructureResults(SimulationWorkflowResults):
    """
    Contains definitions for results of an electronic structure simulation.
    """

    dos = Quantity(
        type=ElectronicDensityOfStates,
        description="""
        Reference to the electronic density of states output.
        """,
    )


m_package.__init_metainfo__()
