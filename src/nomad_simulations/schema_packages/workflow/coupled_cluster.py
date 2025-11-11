from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .beyond_hf import BeyondHFMethod, BeyondHFResults, BeyondHFWorkflow

m_package = SchemaPackage()


class HFCCMethod(BeyondHFMethod):
    _label = 'HF+CC workflow parameters'


class HFCCResults(BeyondHFResults):
    _label = 'HF+CC workflow results'


class HFCCWorkflow(BeyondHFWorkflow):
    """
    Definitions for Coupled-Cluster calculations based on HF (HF → CC).
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = HFCCMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = HFCCResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the HF and CC single-point workflows in the HF-CC workflow.
        """
        super().normalize(archive, logger)

        # Name the last task CC if it is unnamed
        if self.tasks and not self.tasks[-1].name:
            self.tasks[-1].name = 'CC'


m_package.__init_metainfo__()
