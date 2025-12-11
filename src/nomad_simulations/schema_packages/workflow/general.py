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

CONVERGENCE_QUANTITY_MAPPING = {
    'force:maximum' : 'workflow2.results.final_force_maximum',
    'potential:rms' : 'data.outputs[*].scf_steps.delta_potential_rms',
    'energy:absolute': 'data.outputs[*].scf_steps.delta_energies_total',
    'charge:absolute' : 'data.outputs[*].scf_steps.delta_density_rms',
    'force:absolute' : 'data.outputs[*].scf_steps.delta_force_abs'
    }

class SimulationTask(Task):
    pass


class WorkflowConvergenceTarget(ArchiveSection):
    """
    A section for defining convergence targets.

    Calculations are converged w.r.t. to different parameters. This section holds the parameter name
    and the unit of the convergence parameter.
    """

    convergence_parameter_name = Quantity(
        type=MEnum('energy', 'force', 'potential', 'charge', 'density'),
        description="""
        Name of the convergence parameter.

        Available quantites are: `'energy'`, `'force'`, `'potential'`, `'charge'`, `'density'`.
        """
    )

    convergence_threshold = Quantity(
        type=np.float64,
        description="""
        Numerical value of the parameter that is converged.
        """
    )

    threshold_unit = Quantity(
        type=str,
        description = """
        Unit of the convergence threshold.
        """
    )

    # This is copied from PR #191 https://github.com/nomad-coe/nomad-simulations/pull/191
    # TODO @ND: Do all of them apply?
    threshold_type = Quantity(
        type=MEnum('absolute', 'relative', 'maximum', 'rms', 'residuum'),
        description="""
            Specifies the mathematical method used to evaluate convergence between successive self-consistent field (SCF) iterations. 
    This determines how differences between iterations are calculated and compared against the convergence threshold.
    
    The available comparison modes are:
    
    | Mode | Description |
    | --------- | -------------------------------- |
    | `'absolute'` | Measures the absolute difference between two subsequent iterations (e.g., |E_n - E_{n-1}|). Most common for energy convergence. |
    | `'relative'` | Calculates the relative difference as a fraction of the total property value (e.g., |E_n - E_{n-1}|/|E_n|). Useful when the magnitude of the property varies widely across systems. |
    | `'residuum'` | Computes the absolute difference between the current value and the value estimated from the wavefunction at the start of the step. Often used for evaluating convergence of the electron density. |
    | `'maximum'` | Reports the maximum absolute difference across all components of a multi-component property (e.g., max|F_i,n - F_i,{n-1}| for forces). Suitable for vector quantities like forces or stress tensor elements. |
    | `'rms'` | Calculates the root mean square of differences across all components (e.g., √(∑|F_i,n - F_i,{n-1}|²/N)). Provides a statistical measure of overall convergence for multi-component properties. |
    
    The mode used affects both convergence behavior and computational efficiency. Different codes may default to different comparison modes for the same physical property.
        """,
    )


class WorkflowConvergenceResults(ArchiveSection):
    """
    Results of the workflow convergence. This describes if convergence targets have been met during the calculation.
    """

    convergence_target_ref = Quantity(
        type=WorkflowConvergenceTarget,
        description="""
        Reference to the workflow convergence target.    
        """
    )

    is_reached = Quantity(
        type=bool,
        description="""
        Convergence target was reached (true) or not (false).
        """
    )


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

    convergence = SubSection(sub_section=WorkflowConvergenceTarget.m_def, repeats=True)

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
        """
    )

    convergence = SubSection(sub_section=WorkflowConvergenceResults.m_def, repeats=True)


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
        Populate the convergence according the to convergence targets.

        TODO this works only for SCF output so far, needs to also consider geometry optimizations
        """
        if not archive.data or not archive.data.outputs:
            return
        logger = self.map_convergence.__annotations__['logger']

        # check convergence targets in model and populate convergence results in results
        convergence_results = []
        all_reached = None
        convergence_targets = self.method.get('convergence')
        if convergence_targets is None:
            return
        for convergence_target in convergence_targets:
            parameter_name = convergence_target.get('convergence_parameter_name')
            threshold_type = convergence_target.get('threshold_type')
            unit = convergence_target.get('threshold_unit')
            if parameter_name is None or threshold_type is None or unit is None:
                continue
            # do last step of path manually because jmespath only returns the raw values
            # and not quantites - TODO this is pretty much a hack, is there a better solution?
            quantity_path = CONVERGENCE_QUANTITY_MAPPING[f'{parameter_name}:{threshold_type}'].split('.')
            quantity_name = quantity_path[-1]
            quantity_path = '.'.join(quantity_path[:-1])
            quantity_values = jmespath.search(
                quantity_path,
                archive
            )
            if quantity_values is None:
                continue
            if isinstance(quantity_values, list):
               convergence_data = quantity_values[-1][quantity_name]
            else:
                convergence_data = quantity_values[quantity_name]
            threshold = convergence_target['convergence_threshold']
            convergence_result = WorkflowConvergenceResults()
            convergence_result.convergence_target_ref = convergence_target
            converged = False
            # TODO @all: For some reason threshold is just a value and not a quantity
            # I don't know how or where to fix this: It is a quantity in the parser (with its unit)
            # and somehow here it is just a value. Can we have it as a quantity?
            if isinstance(convergence_data, Iterable) and len(convergence_data.shape) > 0: # the threshold is relative
                convergence_data = convergence_data.to(unit)
                converged = abs(convergence_data[-2].magnitude - convergence_data[-1].magnitude) <= threshold
            else: # the threshold is absolute
                converged = convergence_data.to(unit).magnitude < threshold
            if converged:
                convergence_result.is_reached = True
                all_reached = True if all_reached is None else all_reached
            else:
                convergence_result.is_reached = False
                all_reached = False
            convergence_results.append(convergence_result)
        self.results.convergence = convergence_results

        # set converged for self
        if self.results.get('is_converged') is None and all_reached is not None:
            self.results.is_converged = all_reached
        else:
            if not self.results.get('is_converged') == all_reached:
                logger.warning('Derived and parsed state of convergence do not agree.')
                pass
            

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
