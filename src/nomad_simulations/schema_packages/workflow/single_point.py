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

    def map_inputs(self, archive: EntryArchive, logger: BoundLogger):
        super().map_inputs(archive, logger)
        if archive.data:
            if archive.data.model_method:
                self.inputs.append(
                    Link(name='Input method', section=archive.data.model_method[0])
                )

            if archive.data.model_system:
                self.inputs.append(
                    Link(name='Input system', section=archive.data.model_system[0])
                )

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)
        if len(self.tasks) != 1:
            logger.error(INCORRECT_N_TASKS)
            return
        self.tasks[0].name = self.task_label

        # add inputs to calculation inputs
        self.tasks[0].inputs.extend(
            [inp for inp in self.inputs if inp not in self.tasks[0].inputs]
        )

        # add outputs of calculation to outputs
        self.outputs.extend(
            [out for out in self.tasks[0].outputs if out not in self.outputs]
        )


m_package.__init_metainfo__()
