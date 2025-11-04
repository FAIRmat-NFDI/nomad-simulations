from nomad.datamodel import EntryArchive
from nomad.metainfo import SchemaPackage
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.utils import log

from .general import (
    INCORRECT_N_TASKS,
    ElectronicStructureResults,
    SerialWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)

m_package = SchemaPackage()


class BeyondHFModel(SimulationWorkflowModel):
    _label = 'HF+ workflow parameters'


class BeyondHFResults(SimulationWorkflowResults):
    """
    Contains references to HF outputs (baseline) and extended post-HF results.
    """

    _label = 'HF+ workflow results'

    # Baseline HF electronic-structure results (single)
    # Reuse ElectronicStructureResults, consistent with beyond_dft.py
    from nomad.metainfo import (
        SubSection,  # local import to mirror beyond_dft.py pattern
    )

    hf = SubSection(sub_section=ElectronicStructureResults)

    # Extended post-HF electronic-structure results (repeatable)
    ext = SubSection(sub_section=ElectronicStructureResults, repeats=True)


class BeyondHFWorkflow(SerialWorkflow):
    """
    Base workflow for post-HF methods (e.g., HF → CC, HF → CI).
    """

    @log
    def map_inputs(self, archive: EntryArchive) -> None:
        if not self.model:
            self.model = BeyondHFModel()
        logger = self.map_inputs.__annotations__['logger']
        super().map_inputs(archive, logger=logger)

    @log
    def map_outputs(self, archive: EntryArchive) -> None:
        if not self.results:
            self.results = BeyondHFResults()
        logger = self.map_outputs.__annotations__['logger']
        super().map_outputs(archive, logger=logger)

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the HF and the extended single-point workflow.
        """
        super().normalize(archive, logger)

        if len(self.tasks) < 2:
            logger.error(INCORRECT_N_TASKS)
            return

        if not self.name:
            self.name: str = self.m_def.name

        # Name the first task HF if it is unnamed
        if not self.tasks[0].name:
            self.tasks[0].name = 'HF'


m_package.__init_metainfo__()
