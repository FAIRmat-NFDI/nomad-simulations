from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.workflow import Link, Task
from structlog.stdlib import BoundLogger

from .general import SimulationWorkflow


class GeometryOptimization(SimulationWorkflow):
    """
    Definitions for geometry optimization workflow.
    """

    def normalize(self, archive: EntryArchive, logger: BoundLogger) -> None:
        """
        Specify the inputs and outputs of the tasks as the model system.
        """
        super().normalize(archive, logger)

        def to_system_links(task: Task) -> None:
            task.inputs = [
                Link(name='Input system', section=link.section.model_system_ref)
                for link in task.inputs
                if link.section and link.section.model_system_ref
            ]
            task.outputs = [
                Link(name='Output system', section=link.section.model_system_ref)
                for link in task.inputs
                if link.section and link.section.model_system_ref
            ]

        to_system_links(self)
        for task in self.tasks:
            to_system_links(task)
