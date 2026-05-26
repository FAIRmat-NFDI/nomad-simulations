from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage, SubSection
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_method import OrbitalLocalization
from nomad_simulations.schema_packages.utils import log

from .beyond_hf import BeyondHFMethod, BeyondHFResults, BeyondHFWorkflow
from .general import (
    INCORRECT_N_TASKS,
    ElectronicStructureResults,
    SerialWorkflow,
    SimulationWorkflowMethod,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


class HFCCMethod(BeyondHFMethod):
    _label = 'HF+CC workflow parameters'


class HFCCResults(BeyondHFResults):
    _label = 'HF+CC workflow results'


class LocalCCWorkflowMethod(SimulationWorkflowMethod):
    _label = 'local-CC workflow parameters'

    orbital_localization = SubSection(
        sub_section=OrbitalLocalization.m_def,
        repeats=False,
        description="""
        Orbital localization or local-space construction used before the local
        coupled-cluster correlation treatment. The reference calculation may be
        HF, DFT/Kohn-Sham, or another mean-field-like calculation.
        """,
    )


class LocalCCWorkflowResults(SimulationWorkflowResults):
    _label = 'local-CC workflow results'


class HFLocalCCMethod(LocalCCWorkflowMethod):
    _label = 'HF+local-CC workflow parameters'


class HFLocalCCResults(LocalCCWorkflowResults):
    _label = 'HF+local-CC workflow results'

    hf = SubSection(sub_section=ElectronicStructureResults)

    ext = SubSection(sub_section=ElectronicStructureResults, repeats=True)


class DFTLocalCCMethod(LocalCCWorkflowMethod):
    _label = 'DFT-reference local-CC workflow parameters'


class DFTLocalCCResults(LocalCCWorkflowResults):
    _label = 'DFT-reference local-CC workflow results'

    dft = SubSection(sub_section=ElectronicStructureResults)

    ext = SubSection(sub_section=ElectronicStructureResults, repeats=True)


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


class LocalCCWorkflow(SerialWorkflow):
    """
    Common workflow for local coupled-cluster correlation treatments.

    The conceptual steps are reference calculation, orbital localization or
    local-space construction, and local coupled cluster. The reference
    calculation supplies orbitals; the final method is a correlated wavefunction
    treatment.
    """

    _reference_task_name = 'Reference'
    _method_cls = LocalCCWorkflowMethod
    _results_cls = LocalCCWorkflowResults

    method = SubSection(sub_section=LocalCCWorkflowMethod.m_def)

    results = SubSection(sub_section=LocalCCWorkflowResults.m_def)

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.method:
            self.method = self._method_cls()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = self._results_cls()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        super().normalize(archive, logger)

        if not self.name:
            self.name = self.m_def.name
        if self.tasks and not self.tasks[0].name:
            self.tasks[0].name = self._reference_task_name

        if len(self.tasks) != 3:
            logger.error(INCORRECT_N_TASKS)
            return

        if not self.tasks[1].name:
            self.tasks[1].name = 'Orbital localization'
        if not self.tasks[2].name:
            self.tasks[2].name = 'Local CC'


class HFLocalCCWorkflow(LocalCCWorkflow):
    """
    Definitions for local coupled-cluster calculations based on HF
    (HF -> orbital localization -> local CC).
    """

    _reference_task_name = 'HF'
    _method_cls = HFLocalCCMethod
    _results_cls = HFLocalCCResults

    method = SubSection(sub_section=HFLocalCCMethod.m_def)

    results = SubSection(sub_section=HFLocalCCResults.m_def)


class DFTLocalCCWorkflow(LocalCCWorkflow):
    """
    Definitions for local coupled-cluster calculations using a DFT/Kohn-Sham
    reference (DFT reference -> orbital localization -> local CC).

    DFT provides the reference orbitals. The final local coupled-cluster step is
    a correlated wavefunction treatment, not a DFT approximation.
    """

    _reference_task_name = 'DFT'
    _method_cls = DFTLocalCCMethod
    _results_cls = DFTLocalCCResults

    method = SubSection(sub_section=DFTLocalCCMethod.m_def)

    results = SubSection(sub_section=DFTLocalCCResults.m_def)


m_package.__init_metainfo__()
