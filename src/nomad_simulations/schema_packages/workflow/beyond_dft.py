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


class BeyondDFTModel(SimulationWorkflowModel):
    label = 'DFT+ workflow parameters'


class BeyondDFTResults(SimulationWorkflowResults):
    """
    Contains reference to DFT outputs.
    """

    label = 'DFT+ workflow results'

    dft = SubSection(sub_section=ElectronicStructureResults)

    ext = SubSection(sub_section=ElectronicStructureResults)


class BeyondDFTWorkflow(SerialWorkflow):
    """
    Definitions for workflows based on DFT.
    """

    def map_inputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = BeyondDFTModel()
        super().map_inputs(archive, logger)

    def map_outputs(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.results:
            self.results = BeyondDFTResults()
        super().map_outputs(archive, logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the DFT and the extended single point workflow.
        """
        super().normalize(archive, logger)

        if len(self.tasks) != 2:
            logger.error(INCORRECT_N_TASKS)
            return

        if not self.name:
            self.name: str = self.m_def.name

        if not self.tasks[0].name:
            self.tasks[0].name = 'DFT'


class DFTGWModel(BeyondDFTModel):
    label = 'DFT+GW workflow parameters'


class DFTGWResults(BeyondDFTResults):
    label = 'DFT+GW workflow results'


class DFTGWWorkflow(BeyondDFTWorkflow):
    """
    Definitions for GW calculations based on DFT.
    """

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = DFTGWModel()

        if not self.results:
            self.results = DFTGWResults()

        super().normalize(archive, logger)

        if self.task and not self.task[-1].name:
            self.task[-1].name = 'GW'


class DFTTBModel(BeyondDFTModel):
    label = 'DFT+TB workflow parameters'


class DFTTBResults(BeyondDFTResults):
    label = 'DFT+TB worklfow results'


class DFTTBWorkflow(BeyondDFTWorkflow):
    """
    Definitions for TB calculations based on DFT.
    """

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        if not self.model:
            self.model = DFTTBModel()

        if not self.results:
            self.results = DFTTBResults()

        super().normalize(archive, logger)

        if self.tasks and not self.tasks[-1].name:
            self.tasks[-1].name = 'TB'


m_package.__init_metainfo__()
