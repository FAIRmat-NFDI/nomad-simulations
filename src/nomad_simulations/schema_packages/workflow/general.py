from nomad.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task, Workflow
from nomad.metainfo import Quantity, SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem

INCORRECT_N_TASKS = 'Incorrect number of tasks found.'

m_package = SchemaPackage()


class SimulationWorkflowModel(ArchiveSection):
    """
    Base class for simulation workflow model sub-section definition.
    """

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


class SimulationWorkflowResults(ArchiveSection):
    """
    Base class for simulation workflow results sub-section definition.
    """

    final_system = Quantity(
        type=ModelSystem,
        description="""
        Reference to the final model_system.
        """,
    )


class SimulationWorkflow(Workflow):
    """
    Base class for simulation workflows.
    """

    model_label = 'Input model'

    results_label = 'Output results'

    model = SubSection(sub_section=SimulationWorkflowModel.m_def)

    results = SubSection(sub_section=SimulationWorkflowResults.m_def)

    def generate_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = SimulationWorkflowModel()
        self.model.initial_method = archive.data.outputs[0].model_method_ref
        self.model.initial_system = archive.data.outputs[0].model_system_ref

        # set method as inputs
        self.inputs.append(Link(name=self.model_label, section=self.model))

    def generate_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.results:
            self.results = SimulationWorkflowResults()
        self.results.final_system = archive.data.outputs[-1].model_system_ref

        # set results as outputs
        self.outputs.append(Link(name=self.results_label, section=self.results))

    def generate_tasks(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Generate tasks from archive data outputs. Tasks are ordered and linked based
        on the execution time of the calculation corresponding to the output.
        By default, the tasks follow the order of the outputs and are linked sequentially.
        """
        # default should to serial execution
        times: list[tuple[float, float]] = list(
            [
                (o.wall_start or n, o.wall_end or n)
                for n, o in enumerate(archive.data.outputs)
            ]
        )
        times.sort(key=lambda x: x[0])
        # current parent task
        parent_n = 0
        parent_outputs: list[Link] = []
        for n, time in enumerate(times):
            task = Task(
                outputs=[
                    Link(
                        name='Output',
                        section=archive.data.outputs[n],
                    )
                ],
            )
            self.tasks.append(task)
            # link tasks based on overlap in execution time
            if time[0] >= times[parent_n][1]:
                # if no overlap, assign outputs of parent as input to next task
                task.inputs.extend(
                    [
                        Link(name='Input', section=output.section)
                        for output in parent_outputs or task.outputs
                    ]
                )
                # assign first parent outputs as workflow inputs
                if not self.inputs:
                    self.inputs.extend(task.inputs)
                # assign as new parent
                parent_n = n
                # reset outputs
                parent_outputs = list(task.outputs)
            else:
                parent_outputs.extend(task.outputs)
                # if overlap, assign parent outputs to task inputs
                task.inputs.extend(
                    [
                        Link(name='Input', section=output.section)
                        for output in self.tasks[parent_n or n].outputs
                    ]
                )

        if not self.outputs:
            # assign parent outputs as workflow outputs
            self.outputs.extend(parent_outputs)

    def normalize(self, archive: EntryArchive, logger: BoundLogger):
        if not archive.data or not archive.data.outputs:
            return

        if not self.inputs:
            self.generate_inputs(archive, logger)

        if not self.outputs:
            self.generate_outputs(archive, logger)

        if not self.tasks:
            self.generate_tasks(archive, logger)


m_package.__init_metainfo__()
