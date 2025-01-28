from nomad.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task, Workflow
from nomad.metainfo import SubSection
from structlog.stdlib import BoundLogger

INCORRECT_N_TASKS = 'Incorrect number of tasks found.'


class SimulationWorkflowMethod(ArchiveSection):
    """
    Base class for simulation workflow method sub-section definition.
    """

    pass


class SimulationWorkflowResults(ArchiveSection):
    """
    Base class for simulation workflow results sub-section definition.
    """

    pass


class SimulationWorkflow(Workflow):
    """
    Base class for simulation workflows.
    """

    method = SubSection(sub_section=SimulationWorkflowMethod.m_def)

    results = SubSection(sub_section=SimulationWorkflowResults.m_def)

    def normalize(self, archive: EntryArchive, logger: BoundLogger):
        """
        Generate tasks from the archive data outputs.
        """
        if not archive.data or not archive.data.outputs:
            return

        # generate tasks from outputs
        if not self.tasks:
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

        if not self.method:
            self.method = SimulationWorkflowMethod()

        if not self.results:
            self.results = SimulationWorkflowResults()

        # set method as inputs
        self.inputs.append(Link(name='Input method', section=self.method))

        # set results as outputs
        self.outputs.append(Link(name='Ouput results', section=self.results))
