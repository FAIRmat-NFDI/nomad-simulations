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

    Child classes define specific physical properties
    (e.g., energy, force) with proper units. The base class handles all convergence
    checking logic based on the threshold_type enum.
    """

    threshold: Quantity = None

    threshold_type = Quantity(
        type=MEnum('absolute', 'relative', 'maximum', 'rms', 'residuum'),
        description=r"""Specifies the mathematical method used to evaluate convergence between successive self-consistent field (SCF) iterations.
This determines how differences between iterations are calculated and compared against the convergence threshold.

The available comparison modes are:

| Mode | Description |
| --------- | -------------------------------- |
| `'absolute'` | Measures the absolute difference between two subsequent iterations (e.g., \|E_n - E_{n-1}\|). Most common for energy convergence. |
| `'relative'` | Calculates the relative difference as a fraction of the total property value (e.g., \|E_n - E_{n-1}\|/\|E_n\|). Useful when the magnitude of the property varies widely across systems. |
| `'residuum'` | Computes the absolute difference between the current value and the value estimated from the wavefunction at the start of the step. Often used for evaluating convergence of the electron density. |
| `'maximum'` | Reports the maximum absolute difference across all components of a multi-component property (e.g., max\|F_i,n - F_i,{n-1}\| for forces). Suitable for vector quantities like forces or stress tensor elements. |
| `'rms'` | Calculates the root mean square of differences across all components (e.g., √(∑\|F_i,n - F_i,{n-1}\|²/N)). Provides a statistical measure of overall convergence for multi-component properties. |

The mode used affects both convergence behavior and computational efficiency. Different codes may default to different comparison modes for the same physical property.
        """,
    )

    # Class attribute to be overridden in child classes
    # Should be set to the path to the convergence property in outputs
    # e.g., 'scf_steps.delta_energies_total' for energy convergence
    _convergence_property_path: str = None

    def _get_convergence_value(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> float | np.ndarray | None:
        """
        Extract the value to check for convergence from the archive.

        This base implementation provides a generalized approach that searches for
        the property specified in `_convergence_property_path`. Child classes can
        override this for custom extraction logic if needed.

        Returns:
            The value to check (should already be converted to appropriate units),
            or None if the value cannot be determined.
        """
        if self._convergence_property_path is None:
            logger.warning(
                f'{self.__class__.__name__} does not define _convergence_property_path. '
                f'Either set this class attribute or override _get_convergence_value().'
            )
            return None

        try:
            # Navigate to the last output
            if not archive.data or not archive.data.outputs:
                return None

            # TODO: Should this be hardcoded to [-1]? For multi-step workflows (e.g., geometry
            # optimization), we may need to check convergence at specific output indices rather
            # than always using the last output.
            last_output = archive.data.outputs[-1]

            # Parse the property path and navigate through nested attributes
            path_parts = self._convergence_property_path.split('.')
            current_obj = last_output

            for part in path_parts:
                if current_obj is None:
                    return None
                current_obj = getattr(current_obj, part, None)

            if current_obj is None:
                return None

            # Handle the value: extract last element if it's an array with units
            if hasattr(current_obj, '__getitem__'):
                value = current_obj[-1]
            else:
                value = current_obj

            # Convert to magnitude if it has units
            if hasattr(value, 'magnitude'):
                # Get the unit from the threshold to ensure consistent conversion
                if hasattr(self.threshold, 'units'):
                    target_unit = str(self.threshold.units)
                    value = value.to(target_unit).magnitude
                else:
                    value = value.magnitude

            return value

        except (AttributeError, IndexError, TypeError) as e:
            logger.debug(
                f'Could not extract convergence value from {self._convergence_property_path}: {e}'
            )
        return None

    def _check_absolute(self, value: float) -> bool:
        """Check absolute convergence: |value| < threshold"""
        if self.threshold is None:
            return False
        # threshold may be a pint Quantity - get magnitude if so
        threshold_val = (
            self.threshold.magnitude
            if hasattr(self.threshold, 'magnitude')
            else self.threshold
        )
        # Use <= to allow exact zero with zero threshold
        return bool(abs(value) <= threshold_val)

    def _check_relative(self, value: float, reference: float) -> bool:
        """Check relative convergence: |value|/|reference| < threshold"""
        if self.threshold is None:
            return False
        # Special case: both zero means converged
        if abs(reference) < 1e-15 and abs(value) < 1e-15:
            return True
        # Cannot compute relative if reference is zero
        if abs(reference) < 1e-15:
            return False
        # threshold may be a pint Quantity - get magnitude if so
        threshold_val = (
            self.threshold.magnitude
            if hasattr(self.threshold, 'magnitude')
            else self.threshold
        )
        return bool(abs(value / reference) < threshold_val)

    def _check_maximum(self, values: np.ndarray) -> bool:
        """Check maximum convergence: max(|values|) < threshold"""
        if self.threshold is None:
            return False
        # threshold may be a pint Quantity - get magnitude if so
        threshold_val = (
            self.threshold.magnitude
            if hasattr(self.threshold, 'magnitude')
            else self.threshold
        )
        return bool(np.max(np.abs(values)) < threshold_val)

    def _check_rms(self, values: np.ndarray) -> bool:
        """Check RMS convergence: sqrt(mean(values²)) < threshold"""
        if self.threshold is None:
            return False
        # threshold may be a pint Quantity - get magnitude if so
        threshold_val = (
            self.threshold.magnitude
            if hasattr(self.threshold, 'magnitude')
            else self.threshold
        )
        return bool(np.sqrt(np.mean(values**2)) < threshold_val)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> bool | None:
        """
        Check if convergence criterion is met.

        Returns:
            True if converged, False if not, None if cannot be determined.
        """
        if not archive.data:
            return None

        try:
            value = self._get_convergence_value(archive, logger)
            if value is None:
                return None

            conv_type = self.threshold_type or 'absolute'

            # Handle scalar vs array values
            if isinstance(value, int | float | np.floating):
                # Scalar value - use absolute or relative
                if conv_type == 'absolute':
                    return self._check_absolute(value)
                elif conv_type == 'relative':
                    # For relative, child class should provide reference
                    logger.warning(
                        f'Relative convergence requires reference value in '
                        f'{self.__class__.__name__}'
                    )
                    return None
                else:
                    return self._check_absolute(value)

            elif isinstance(value, np.ndarray):
                # Array value - can use maximum or rms
                if conv_type == 'maximum':
                    return self._check_maximum(value)
                elif conv_type == 'rms':
                    return self._check_rms(value)
                elif conv_type == 'absolute':
                    # For array, treat as maximum
                    return self._check_maximum(value)
                else:
                    return self._check_maximum(value)

        except Exception as e:
            logger.debug(
                f'Could not check convergence for {self.__class__.__name__}: {e}'
            )
        return None


class EnergyConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for energy in SCF or optimization workflows.
    The threshold_type determines how energy convergence is evaluated.
    """

    threshold = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Energy convergence threshold.
        """,
    )

    # Property path for automatic extraction
    _convergence_property_path = 'scf_steps.delta_energies_total'


class ForceConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for forces in optimization or SCF workflows.
    The threshold_type determines how force convergence is evaluated.
    """

    threshold = Quantity(
        type=np.float64,
        unit='newton',
        description="""
        Force convergence threshold.
        """,
    )

    # Note: ForceConvergenceTarget has multiple extraction paths depending on threshold_type
    # and data availability. The simple path approach works for 'absolute' type:
    _convergence_property_path = 'scf_steps.delta_force_abs'

    # TODO: The current implementation below has custom logic for different convergence types
    # and fallback paths. Consider whether to:
    # 1. Keep custom implementation for complex cases like this
    # 2. Extend the base class to support multiple property paths with conditions
    # 3. Use the simple path for common case and override only for special cases

    def _get_convergence_value(
        self, archive: EntryArchive, logger: BoundLogger
    ) -> float | np.ndarray | None:
        """Extract force convergence value from archive."""
        try:
            conv_type = self.threshold_type or 'maximum'

            # For maximum force in geometry optimization, check workflow level
            if (
                conv_type == 'maximum'
                and hasattr(archive, 'workflow2')
                and archive.workflow2
            ):
                final_force_max = archive.workflow2.results.final_force_maximum
                if final_force_max is not None:
                    return final_force_max.to('newton').magnitude

            # For absolute (SCF force delta) - could use base class with _convergence_property_path
            if conv_type == 'absolute' and archive.data.outputs:
                delta_forces = archive.data.outputs[-1].scf_steps.delta_force_abs
                if delta_forces is not None:
                    return delta_forces[-1].to('newton').magnitude

            # Fallback: get force array from last output
            if archive.data.outputs:
                forces = archive.data.outputs[-1].total_forces
                if forces is not None and len(forces) > 0:
                    # Get force values and convert to magnitudes if needed
                    force_values = forces[-1].value
                    if hasattr(force_values, 'magnitude'):
                        force_values = force_values.to('newton').magnitude
                    # Return force magnitudes for each atom
                    force_magnitudes = np.linalg.norm(force_values, axis=1)
                    return force_magnitudes
        except (AttributeError, IndexError, TypeError) as e:
            logger.debug(f'Could not extract force convergence value from outputs: {e}')
        return None


class PotentialConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for potential in SCF workflows.
    The threshold_type determines how potential convergence is evaluated.
    """

    threshold = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Potential convergence threshold.
        """,
    )

    # Property path for automatic extraction
    _convergence_property_path = 'scf_steps.delta_potential_rms'


class ChargeConvergenceTarget(WorkflowConvergenceTarget):
    """
    Convergence target for charge/electron density in SCF workflows.
    The threshold_type determines how density convergence is evaluated.
    """

    threshold = Quantity(
        type=np.float64,
        unit='coulomb',
        description="""
        Charge/density convergence threshold.
        """,
    )

    # Property path for automatic extraction
    _convergence_property_path = 'scf_steps.delta_density_rms'


class SimulationWorkflowModel(ArchiveSection):
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

    convergence_targets = SubSection(
        sub_section=WorkflowConvergenceTarget.m_def, repeats=True
    )

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not archive.data:
            return

        # set references to initial system and method
        if not self.initial_system and archive.data.model_system:
            self.initial_system = archive.data.model_system[0]
        if not self.initial_method and archive.data.model_method:
            self.initial_method = archive.data.model_method[0]


# Backwards-compatible alias used across workflows/tests.
class SimulationWorkflowMethod(SimulationWorkflowModel):
    pass


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


class WorkflowConvergenceResults(ArchiveSection):
    """
    Results of workflow convergence checks.

    This class allows for flexible convergence result reporting, especially useful
    in nested workflow hierarchies where convergence results may need to be
    aggregated from multiple sources or represent composite convergence criteria.

    For simple cases, convergence targets can use their built-in `is_reached` field.
    For complex cases (e.g., nested workflows), use this class to reference targets
    and provide aggregated results.
    """

    convergence_target_ref = Quantity(
        type=WorkflowConvergenceTarget,
        description="""
        Reference to the workflow convergence target that this result corresponds to.
        """,
    )

    is_reached = Quantity(
        type=bool,
        description="""
        Indicates whether this convergence target was reached (True) or not (False).
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

    convergence = SubSection(
        sub_section=WorkflowConvergenceResults.m_def,
        repeats=True,
        description="""
        Convergence results for workflows.
        Each result references a convergence target and stores its reached status.
        """,
    )


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
    def map_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if self.method:
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

        # Normalize each convergence target and collect results
        convergence_status = {}  # Map target -> is_reached
        for target in convergence_targets:
            is_reached = target.normalize(archive, logger)
            convergence_status[target] = is_reached

        # Create WorkflowConvergenceResults if needed.
        if not self.results.convergence:
            convergence_results = []
            for target in convergence_targets:
                result = WorkflowConvergenceResults()
                result.convergence_target_ref = target
                result.is_reached = convergence_status[target]
                convergence_results.append(result)
            if convergence_results:
                self.results.convergence = convergence_results

        # Determine overall convergence status
        all_reached = all(
            convergence_status[target]
            for target in convergence_targets
            if convergence_status[target] is not None
        )
        any_checked = any(
            convergence_status[target] is not None for target in convergence_targets
        )

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

    def _resolve_convergence(
        self,
        archive: EntryArchive,
        convergence_targets: list[WorkflowConvergenceTarget],
        logger: BoundLogger,
    ) -> list[WorkflowConvergenceResults]:
        """
        Helper method to resolve convergence targets for outputs.
        Used primarily for multi-step workflows like geometry optimization.

        Creates temporary copies of convergence targets, normalizes them, and returns
        WorkflowConvergenceResults with the convergence status.
        Note: Currently checks convergence against the last output only.
        """
        convergence_results = []

        for target in convergence_targets:
            # Create a copy of the target to avoid modifying the original
            target_copy = target.m_copy(deep=True)

            # For multi-output scenarios, we may need to adjust the archive context
            # This is a simplified approach - child classes can override for more complex logic
            is_reached = target_copy.normalize(archive, logger)

            # Create a result object that holds both the target and the convergence status
            result = WorkflowConvergenceResults()
            # Reference the original target (which is in the archive hierarchy),
            # not the copy (which would be orphaned and cause serialization errors)
            result.convergence_target_ref = target
            result.is_reached = is_reached
            convergence_results.append(result)

        return convergence_results


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
