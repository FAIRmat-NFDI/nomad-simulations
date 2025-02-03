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


class SimulationWorkflow(Workflow):
    """
    Base class for simulation workflows.
    """

    task_label = 'Task'

    model = SubSection(sub_section=SimulationWorkflowModel.m_def)

    results = SubSection(sub_section=SimulationWorkflowResults.m_def)

    def map_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = SimulationWorkflowModel()

        self.model.normalize(archive, logger)

        # set method as inputs
        self.inputs.append(Link(name=self.model.label, section=self.model))

    def map_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.results:
            self.results = SimulationWorkflowResults()

        self.results.normalize(archive, logger)

        # set results as outputs
        self.outputs.append(Link(name=self.results.label, section=self.results))

    def map_tasks(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Generate tasks from archive data outputs. Tasks are ordered and linked based
        on the execution time of the calculation corresponding to the output.
        By default, the tasks follow the order of the outputs and are linked sequentially.
        """
        if not archive.data or not archive.data.outputs:
            return

        # default should to serial execution
        times: list[tuple[float, float]] = list(
            [
                (
                    o.wall_start.magnitude if o.wall_start else n,
                    o.wall_end.magnitude if o.wall_end else n,
                )
                for n, o in enumerate(archive.data.outputs)
            ]
        )
        times.sort(key=lambda x: x[0])
        # current index of parent
        parent_n = 0
        for n, time in enumerate(times):
            task = Task(
                outputs=[
                    Link(
                        name='Outputs',
                        section=archive.data.outputs[n],
                    )
                ],
            )
            self.tasks.append(task)
            # link tasks based on overlap in execution time
            if time[0] >= times[parent_n][1]:
                # assign as new parent
                parent_n = n
                # reset outputs
                self._grouped_tasks.append([n])
            else:
                if not self._grouped_tasks:
                    self._grouped_tasks.append([])
                self._grouped_tasks[-1].append(n)

    def normalize(self, archive: EntryArchive, logger: BoundLogger):
        if not self.inputs:
            self.map_inputs(archive, logger)

        if not self.outputs:
            self.map_outputs(archive, logger)

        # group tasks in parallel
        # assume serial workflow
        self._grouped_tasks = [[n] for n in range(len(self.tasks))]

        if not self.tasks:
            self.map_tasks(archive, logger)

        # add task inputs/outputs to reference
        # TODO do this in TaskReference normalizer
        for task in self.tasks:
            if isinstance(task, TaskReference):
                task.inputs.extend(task.task.inputs)
                task.outputs.extend(task.task.outputs)

        # link successive task groups, first group adds workflow inputs
        for tasks_n, grouped_tasks in enumerate(self._grouped_tasks):
            # assign outputs of previous tasks an input to next tasks
            if tasks_n:
                inputs = [
                    inp
                    for task in [
                        self.tasks[n] for n in self._grouped_tasks[tasks_n - 1]
                    ]
                    for inp in task.outputs
                ]
            else:
                inputs = self.inputs
            for n in grouped_tasks:
                self.tasks[n].inputs.extend(inputs)
                if isinstance(self.tasks[n], TaskReference):
                    self.tasks[n].task.inputs.extend(inputs)

        if self._grouped_tasks:
            # add inputs of first group to workflow inputs
            self.inputs.extend(
                [
                    inp
                    for task in [self.tasks[n] for n in self._grouped_tasks[0]]
                    for inp in task.inputs
                    if inp not in self.inputs
                ]
            )

            # add outputs of last group to workflow outputs
            self.outputs.extend(
                [
                    out
                    for task in [self.tasks[n] for n in self._grouped_tasks[-1]]
                    for out in task.outputs
                    if out not in self.outputs
                ]
            )


class SerialWorkflow(SimulationWorkflow):
    """
    Base class for workflows where tasks are executed sequentially.
    """

    def map_tasks(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().map_tasks(archive, logger)
        for n, task in enumerate(self.tasks):
            if not task.name:
                task.name = f'{self.task_label} {n}'


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
