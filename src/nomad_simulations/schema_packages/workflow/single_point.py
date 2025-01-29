from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.workflow import Task
from nomad.metainfo import SchemaPackage
from structlog.stdlib import BoundLogger

from .general import (
    INCORRECT_N_TASKS,
    SimulationWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


class SinglePointModel(SimulationWorkflowModel):
    """
    Contains definitions for the input model of a single point workflow.
    """

    pass


class SinglePointResults(SimulationWorkflowResults):
    """
    Contains defintions for the results of a single point workflow.
    """

    pass


class SinglePoint(SimulationWorkflow):
    """
    Definitions for single point workflow.
    """

    task_label = 'Calculation'

    def generate_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = SinglePointModel()
        super().generate_inputs(archive, logger)

    def generate_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.results:
            self.results = SinglePointResults()
        super().generate_outputs(archive, logger)

    def generate_tasks(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if len(archive.data.outputs) != 1:
            logger.error(INCORRECT_N_TASKS)

        task = Task(name=self.task_label)
        task.inputs.extend(self.inputs)
        task.outputs.extend(self.outputs)

        self.tasks.append(task)


m_package.__init_metainfo__()
