from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

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

    _label = 'Single point model'


class SinglePointResults(SimulationWorkflowResults):
    """
    Contains defintions for the results of a single point workflow.
    """

    _label = 'Single point results'


class SinglePoint(SimulationWorkflow):
    """
    Definitions for single point workflow.
    """

    _task_label = 'Calculation'

    @log
    def map_inputs(self, archive: EntryArchive):
        if not self.model:
            self.model = SinglePointModel()

        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive):
        if not self.results:
            self.results = SinglePointResults()

        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)
        if len(self.tasks) != 1:
            logger.error(INCORRECT_N_TASKS)
            return
        self.tasks[0].name = self._task_label

        # add inputs to calculation inputs
        self.tasks[0].inputs.extend(
            [inp for inp in self.inputs if inp not in self.tasks[0].inputs]
        )

        # add outputs of calculation to outputs
        self.outputs.extend(
            [out for out in self.tasks[0].outputs if out not in self.outputs]
        )


m_package.__init_metainfo__()
