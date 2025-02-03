from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task
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

    label = 'Single point model'


class SinglePointResults(SimulationWorkflowResults):
    """
    Contains defintions for the results of a single point workflow.
    """

    label = 'Single point results'


class SinglePoint(SimulationWorkflow):
    """
    Definitions for single point workflow.
    """

    task_label = 'Calculation'

    def map_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        # if not self.model:
        #     self.model = SinglePointModel()
        # super().map_inputs(archive, logger)
        # no need to wrap model and system
        if not archive.data:
            return
        if archive.data.model_method:
            self.inputs.append(
                Link(name='Input method', section=archive.data.model_method[0])
            )

        if archive.data.model_system:
            self.inputs.append(
                Link(name='Input system', section=archive.data.model_system[0])
            )

    def map_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        # if not self.results:
        #     self.results = SinglePointResults()
        # super().map_outputs(archive, logger)
        # no need to wrap outputs, nothing to add as last task outputs is
        # added in SimulationWorkflow
        pass

    def map_tasks(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().map_tasks(archive, logger)
        if len(self.tasks) != 1:
            logger.error(INCORRECT_N_TASKS)
            return
        self.tasks[0].name = self.task_label


m_package.__init_metainfo__()
