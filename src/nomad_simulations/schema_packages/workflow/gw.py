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

# TODO use defs in beyond_dft


class DFTGWModel(SimulationWorkflowModel):
    label = 'DFT+GW workflow parameters'


class DFTGWResults(SimulationWorkflowResults):
    """
    Contains references to DFT and GW outputs.
    """

    label = 'DFT+GW workflow results'

    dft = SubSection(sub_section=ElectronicStructureResults)

    gw = SubSection(sub_section=ElectronicStructureResults)


class DFTGWWorkflow(SerialWorkflow):
    """
    Definitions for GW calculation based on DFT workflow.
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = DFTGWModel()
        logger = self.map_input.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = DFTGWResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the DFT and GW single point workflows in the DFT-GW workflow.
        """
        super().normalize(archive, logger)

        if not self.name:
            self.name: str = 'DFT+GW'

        if len(self.tasks) != 2:
            logger.error(INCORRECT_N_TASKS)
            return


m_package.__init_metainfo__()
