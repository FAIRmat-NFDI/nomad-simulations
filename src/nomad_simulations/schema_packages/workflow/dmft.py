from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .beyond_dft import BeyondDFTModel, BeyondDFTResults, BeyondDFTWorkflow

m_package = SchemaPackage()


class DFTTBDDMFTModel(BeyondDFTModel):
    _label = 'DFT+TB+DMFT workflow parameters'


class DFTTBDMFTResults(BeyondDFTResults):
    _label = 'DFT+TB+DMFT workflow results'


class DFTTBDMFTWorkflow(BeyondDFTWorkflow):
    """
    Definitions for DMFT worklow based on DFT and TB.
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = DFTTBDDMFTModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = DFTTBDMFTResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the DMFT, TB and DFT single point workflows in the DMFT-TB-DFT workflow.
        """

        super().normalize(archive, logger)

        if len(self.tasks) == 3 and not self.tasks[1].name:
            self.tasks[1].name = 'TB'

        if self.tasks and not self.tasks[-1].name:
            self.tasks[-1].name = 'DMFT'


m_package.__init_metainfo__()
