from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .beyond_dft import BeyondDFTModel, BeyondDFTResults, BeyondDFTWorkflow

m_package = SchemaPackage()


class DFTGWModel(BeyondDFTModel):
    _label = 'DFT+GW workflow parameters'


class DFTGWResults(BeyondDFTResults):
    _label = 'DFT+GW workflow results'


class DFTGWWorkflow(BeyondDFTWorkflow):
    """
    Definitions for GW calculations based on DFT.
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = DFTGWModel()
        logger = self.map_inputs.__annotations__['logger']
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

        if self.tasks and not self.tasks[-1].name:
            self.tasks[-1].name = 'GW'


m_package.__init_metainfo__()
