from nomad.actions import TaskQueue
from pydantic import Field
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from nomad.config.models.plugins import ActionEntryPoint


class LegacyCleanupActionEntryPoint(ActionEntryPoint):
    task_queue: str = Field(
        default=TaskQueue.CPU, description='Determines the task queue for this action'
    )

    def load(self):
        from nomad.actions import Action

        from nomad_simulations.actions.legacy_cleanup.activities import cleanup_upload
        from nomad_simulations.actions.legacy_cleanup.workflows import (
            LegacyCleanupWorkflow,
        )

        return Action(
            task_queue=self.task_queue,
            workflow=LegacyCleanupWorkflow,
            activities=[cleanup_upload],
        )


legacy_cleanup_action_entry_point = LegacyCleanupActionEntryPoint(
    name='LegacyContributionsCleanupAction',
    description=(
        'Clean legacy `ModelMethod.contributions` content in stored archives: '
        'prune self-duplicate nested methods and relocate `RelativityModel` '
        'entries to the typed `relativity` subsection. Dry-run by default.'
    ),
)
