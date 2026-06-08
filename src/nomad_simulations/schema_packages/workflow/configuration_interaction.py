from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .beyond_hf import BeyondHFMethod, BeyondHFResults, BeyondHFWorkflow

m_package = SchemaPackage()


class HFCIMethod(BeyondHFMethod):
    _label = 'HF+CI workflow parameters'


class HFCIResults(BeyondHFResults):
    _label = 'HF+CI workflow results'


class HFCIWorkflow(BeyondHFWorkflow):
    """
    Definitions for Configuration-Interaction calculations based on HF (HF → CI).
    """

    method = SubSection(sub_section=HFCIMethod.m_def)

    results = SubSection(sub_section=HFCIResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = HFCIMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = HFCIResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the HF and CI single-point workflows in the HF-CI workflow.
        """
        super().normalize(archive, logger)

        # Name the last task CI if it is unnamed
        if self.tasks and not self.tasks[-1].name:
            self.tasks[-1].name = 'CI'


m_package.__init_metainfo__()
