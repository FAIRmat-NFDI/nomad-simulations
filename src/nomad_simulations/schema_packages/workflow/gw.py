from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

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

    def map_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = DFTGWModel()
        super().map_inputs(archive, logger)

    def map_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.results:
            self.results = DFTGWResults()
        super().map_outputs(archive, logger)

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
