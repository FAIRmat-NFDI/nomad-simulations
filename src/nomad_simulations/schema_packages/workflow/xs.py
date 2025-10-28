import numpy as np
from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .beyond_dft import BeyondDFTModel, BeyondDFTResults, BeyondDFTWorkflow

m_package = SchemaPackage()


class XSModel(BeyondDFTModel):
    _label = 'XS workflow parameters'


class XSResults(BeyondDFTResults):
    _label = 'XS workflow results'


class XSWorkflow(BeyondDFTWorkflow):
    """
    Definitions for XS workflow based in DFT, GW and PhotonPolarizationWorkflow.
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = XSModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = XSResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if self.tasks:
            if not self.tasks[-1].name:
                self.tasks[-1].name = 'PhotonPolarization'
            if len(self.tasks) >= 3 and not self.tasks[1].name:
                self.tasks[1].name = 'GW'

        # TODO fill in results and model


m_package.__init_metainfo__()
