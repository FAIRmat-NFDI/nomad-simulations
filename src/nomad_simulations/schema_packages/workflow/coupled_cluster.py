from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import OrbitalLocalization
from nomad_simulations.schema_packages.utils import log

from .beyond_dft import BeyondDFTMethod, BeyondDFTResults, BeyondDFTWorkflow
from .beyond_hf import BeyondHFMethod, BeyondHFResults, BeyondHFWorkflow

m_package = SchemaPackage()


class HFCCMethod(BeyondHFMethod):
    _label = 'HF+CC workflow parameters'


class HFCCResults(BeyondHFResults):
    _label = 'HF+CC workflow results'


class HFLocalCCMethod(BeyondHFMethod):
    _label = 'HF+local-CC workflow parameters'

    orbital_localization = SubSection(
        sub_section=OrbitalLocalization.m_def,
        repeats=False,
    )


class HFLocalCCResults(BeyondHFResults):
    _label = 'HF+local-CC workflow results'


class DFTLocalCCMethod(BeyondDFTMethod):
    _label = 'DFT+local-CC workflow parameters'


class DFTLocalCCResults(BeyondDFTResults):
    _label = 'DFT+local-CC workflow results'


class HFCCWorkflow(BeyondHFWorkflow):
    """
    Definitions for Coupled-Cluster calculations based on HF (HF → CC).
    """

    method = SubSection(sub_section=HFCCMethod.m_def)

    results = SubSection(sub_section=HFCCResults.m_def)

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


class HFLocalCCWorkflow(BeyondHFWorkflow):
    """
    Definitions for local coupled-cluster calculations based on HF
    (HF -> orbital localization -> local CC).
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = HFLocalCCMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = HFLocalCCResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if self.tasks and len(self.tasks) > 1 and not self.tasks[1].name:
            self.tasks[1].name = 'Orbital localization'
        if self.tasks and not self.tasks[-1].name:
            self.tasks[-1].name = 'Local CC'


class DFTLocalCCWorkflow(BeyondDFTWorkflow):
    """
    Definitions for local coupled-cluster calculations based on DFT
    (DFT -> orbital localization -> local CC).
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = DFTLocalCCMethod()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = DFTLocalCCResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if self.tasks and len(self.tasks) > 1 and not self.tasks[1].name:
            self.tasks[1].name = 'Orbital localization'
        if self.tasks and not self.tasks[-1].name:
            self.tasks[-1].name = 'Local CC'


m_package.__init_metainfo__()
