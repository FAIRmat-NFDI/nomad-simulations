from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .beyond_dft import BeyondDFTMethod, BeyondDFTResults, BeyondDFTWorkflow

m_package = SchemaPackage()


class DMTMaxEntMethod(BeyondDFTMethod):
    _label = 'DMFT+MaxEnt workflow parameters'


class DMTMaxEntResults(BeyondDFTResults):
    _label = 'DMFT+MaxEnt workflow results'


class DMFTMaxEntWorkflow(BeyondDFTWorkflow):
    """
    Definitions for MaxEnt (Maximum Entropy) worklow based on DMFT.
    """

    method = SubSection(sub_section=DMTMaxEntMethod.m_def)

    results = SubSection(sub_section=DMTMaxEntResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = DMTMaxEntMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = DMTMaxEntResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the DMFT and MaxEnt single point workflows in the DMFT-MaxEnt workflow.
        """

        super().normalize(archive, logger)

        if self.tasks:
            if not self.tasks[-1].name:
                self.tasks[-1].name = 'MaxEnt'


m_package.__init_metainfo__()
