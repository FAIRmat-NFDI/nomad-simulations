from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .general import (
    INCORRECT_N_TASKS,
    ElectronicStructureResults,
    SerialWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


class BeyondDFTModel(SimulationWorkflowModel):
    _label = 'DFT+ workflow parameters'


class BeyondDFTResults(SimulationWorkflowResults):
    """
    Contains reference to DFT outputs.
    """

    _label = 'DFT+ workflow results'

    dft = SubSection(sub_section=ElectronicStructureResults)

    ext = SubSection(sub_section=ElectronicStructureResults, repeats=True)


class BeyondDFTWorkflow(SerialWorkflow):
    """
    Definitions for workflows based on DFT.
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = BeyondDFTModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = BeyondDFTResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the DFT and the extended single point workflow.
        """
        super().normalize(archive, logger)

        if len(self.tasks) < 2:
            logger.error(INCORRECT_N_TASKS)
            return

        if not self.name:
            self.name: str = self.m_def.name

        if not self.tasks[0].name:
            self.tasks[0].name = 'DFT'


m_package.__init_metainfo__()
