from nomad.datamodel import EntryArchive
from structlog.stdlib import BoundLogger

from .general import INCORRECT_N_TASKS, SimulationWorkflow


class DFTGWWorkflow(SimulationWorkflow):
    """
    Definitions for GW calculation based on DFT workflow.
    """

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Link the DFT and GW single point workflows in the DFT-GW workflow.
        """
        super().normalize(archive, logger)

        if not self.name:
            self.name = 'DFT+GW'

        if len(self.tasks) != 2:
            logger.error(INCORRECT_N_TASKS)
            return

        if not self.inputs:
            # set inputs to inputs of DFT
            self.inputs = self.tasks[0].task.inputs

        if not self.outputs:
            # set ouputs to outputs of GW
            self.outputs = self.tasks[1].task.outputs

        # link dft and gw workflows
        self.tasks[0].inputs = self.inputs
        self.tasks[0].outputs = self.tasks[0].task.outputs
        self.tasks[1].inputs = self.tasks[0].outputs
        self.tasks[1].outputs = self.outputs
