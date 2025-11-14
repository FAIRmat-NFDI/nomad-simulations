import numpy as np
from nomad.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task, TaskReference, Workflow
from nomad.metainfo import MEnum, Quantity, SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties import ElectronicDensityOfStates
from nomad_simulations.schema_packages.utils import log

# TODO make this a function to check required number of tasks
INCORRECT_N_TASKS = 'Incorrect number of tasks found.'

m_package = SchemaPackage()


class SimulationTask(Task):
    pass


class WorkflowConvergenceTarget(ArchiveSection):
    """
    A section for defining convergence targets.

    Calculations are converged w.r.t. to different parameters. This section holds the parameter name
    and the unit of the convergence parameter.
    """

    # TODO: This most probably needs more explanation, and/or needs to be changed to an Enum to reduce ambiguity when populating.
    convergence_parameter_name = Quantity(
        type=str,
        description="""
        Name of the parameter that is converged, e.g., energy, forces, electron density, ...
        """
    )

    convergence_threshold = Quantity(
        type=np.float64,
        description="""
        Numerical value of the parameter that is converged.
        """
    )

    # This is copied from PR #191 https://github.com/nomad-coe/nomad-simulations/pull/191
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

    convergence_threshold_unit = Quantity(
        type=str,
        description="""
        Unit using the pint UnitRegistry() notation for the `convergence_threshold`.
        """
    )

    is_reached = Quantity(
        type=bool,
        description="""
        Represents if the convergence target was reached (True) or not (False).
        """
    )


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

    is_converged = Quantity(
        type=bool,
        description="""
        Indicates if all convergence targets have been reached (true)
        or not (false)
        """
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

        #TODO test
        # set convergence
        self.is_converged = all(convergence_target.is_reached for convergence_target in self.convergence)

class SimulationWorkflowResults(ArchiveSection):
    """
    Base class for simulation workflow results sub-section definition.
    """

    _label = 'Output results'

    final_outputs = Quantity(
        type=Outputs,
        description="""
        Reference to the final outputs.
        """,
    )

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not archive.data or not archive.data.outputs:
            return

        if not self.final_outputs:
            self.final_outputs = archive.data.outputs[-1]


class SimulationTaskReference(TaskReference, SimulationTask):
    pass


class SimulationWorkflow(Workflow, SimulationTask):
    """
    Base class for simulation workflows.

    It contains sub-sections model and results which are included in inputs and
    outputs, respectively.
    """

    _task_label = 'Task'

    model = SubSection(sub_section=SimulationWorkflowModel.m_def)

    results = SubSection(sub_section=SimulationWorkflowResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = SimulationWorkflowModel()

        if self.model in [inp.section for inp in self.inputs]:
            return

        logger = self.map_inputs.__annotations__['logger']
        self.model.normalize(archive, logger)
        # add method to inputs
        self.inputs.append(Link(name=self.model._label, section=self.model))

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
        
        #Don't generate tasks if not at the root
        if isinstance(self.m_parent, SimulationWorkflowModel):
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

    def normalize(self, archive: EntryArchive, logger: BoundLogger):
        """
        Link tasks based on start and end times.
        """
        if not self.name:
            self.name: str = self.m_def.name

        self.map_inputs(archive, logger=logger)

        self.map_outputs(archive, logger=logger)

        self.map_tasks(archive, logger=logger)


class SerialWorkflow(SimulationWorkflow):
    """
    Base class for workflows where tasks are executed sequentially.
    """

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
