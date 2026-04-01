from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .beyond_dft import BeyondDFTMethod, BeyondDFTResults, BeyondDFTWorkflow
from .general import INCORRECT_N_TASKS

m_package = SchemaPackage()


class DFTTBMethod(BeyondDFTMethod):
    _label = 'DFT+TB workflow parameters'


class DFTTBResults(BeyondDFTResults):
    _label = 'DFT+TB worklfow results'


class DFTTBWorkflow(BeyondDFTWorkflow):
    """
    Definitions for TB calculations based on DFT.
    """

    method = SubSection(sub_section=DFTTBMethod.m_def)

    results = SubSection(sub_section=DFTTBResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = DFTTBMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = DFTTBResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if self.tasks and not self.tasks[-1].name:
            self.tasks[-1].name = 'TB'


m_package.__init_metainfo__()
