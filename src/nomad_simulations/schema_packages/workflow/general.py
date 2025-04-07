from nomad.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task, TaskReference, Workflow
from nomad.metainfo import Quantity, SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties import ElectronicDensityOfStates

INCORRECT_N_TASKS = 'Incorrect number of tasks found.'

m_package = SchemaPackage()


class SimulationTask(Task):
    pass


class SimulationWorkflowModel(ArchiveSection):
    """
    Base class for simulation workflow model sub-section definition.
    """

    label = 'Input model'

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

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not archive.data:
            return

        if not self.initial_system and archive.data.model_system:
            self.initial_system = archive.data.model_system[0]
        if not self.initial_method and archive.data.model_method:
            self.initial_method = archive.data.model_method[0]


class SimulationWorkflowResults(ArchiveSection):
    """
    Base class for simulation workflow results sub-section definition.
    """

    label = 'Output results'

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

    task_label = 'Task'

    model = SubSection(sub_section=SimulationWorkflowModel.m_def)

    results = SubSection(sub_section=SimulationWorkflowResults.m_def)

    def map_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if self.model:
            self.model.normalize(archive, logger)
            # add method to inputs
            self.inputs.append(Link(name=self.model.label, section=self.model))

    def map_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if self.results:
            self.results.normalize(archive, logger)
            # add results to outputs
            self.outputs.append(Link(name=self.results.label, section=self.results))

    def map_tasks(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Generate tasks from archive data outputs. Tasks are ordered and linked based
        on the execution time of the calculation corresponding to the output.
        """
        if not archive.data or not archive.data.outputs:
            return

        outputs = list(archive.data.outputs)
        outputs.sort(key=lambda x: x.wall_start or 0)
        tasks = []
        parent_n = 0
        for n, output in enumerate(outputs):
            task = SimulationTask(
                name=f'{self.task_label} {n}',
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
                parent_n = n
            elif n != parent_n:
                task.inputs.append(Link(name='Linked task', section=tasks[parent_n]))

        self.tasks.extend(tasks)

    def normalize(self, archive: EntryArchive, logger: BoundLogger):
        """
        Link tasks based on start and end times.
        """
        if not self.name:
            self.name: str = self.m_def.name

        if not self.inputs:
            self.map_inputs(archive, logger)

        if not self.outputs:
            self.map_outputs(archive, logger)

        if not self.tasks:
            self.map_tasks(archive, logger)


class SerialWorkflow(SimulationWorkflow):
    """
    Base class for workflows where tasks are executed sequentially.
    """

    def map_tasks(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().map_tasks(archive, logger)
        for n, task in enumerate(self.tasks):
            if not task.name:
                task.name = f'{self.task_label} {n}'

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

        # add oututs of last task to outputs
        self.outputs.extend(
            [out for out in self.tasks[-1].outputs if out not in self.outputs]
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
