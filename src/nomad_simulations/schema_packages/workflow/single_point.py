from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.workflow import Link
from structlog.stdlib import BoundLogger

from .general import INCORRECT_N_TASKS, SimulationWorkflow


class SinglePoint(SimulationWorkflow):
    """
    Definitions for single point workflow.
    """

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Specify the method and system as inputs.
        """
        super().normalize(archive, logger)
        if len(self.tasks) != 1:
            logger.error(INCORRECT_N_TASKS)
            return

        if not self.inputs:
            self.inputs.extend(self.tasks[0].inputs)

        inps: list[Link] = []
        for inp in self.inputs:
            if inp.section and inp.section.model_system_ref:
                inps.append(
                    Link(name='Input system', section=inp.section.model_system_ref)
                )
            if inp.section and inp.section.model_method_ref:
                inps.append(
                    Link(name='Input method', section=inp.section.model_method_ref)
                )
        self.inputs.clear()
        self.inputs.extend(inps)

        # reconnect inputs to link as these are redefined
        self.tasks[0].inputs.clear()
        self.tasks[0].inputs.extend(inps)
