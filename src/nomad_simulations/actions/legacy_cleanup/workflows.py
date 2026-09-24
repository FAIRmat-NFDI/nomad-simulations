from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from nomad_simulations.actions.legacy_cleanup.activities import cleanup_upload
    from nomad_simulations.actions.legacy_cleanup.models import (
        CleanupSingleUploadInput,
        LegacyCleanupWorkflowInput,
    )


@workflow.defn
class LegacyCleanupWorkflow:
    @workflow.run
    async def run(self, data: LegacyCleanupWorkflowInput) -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
        )

        uploads = []
        totals: dict[str, int] = {}
        for upload_id in data.target_upload_ids:
            upload_result = await workflow.execute_activity(
                cleanup_upload,
                CleanupSingleUploadInput(
                    upload_id=upload_id,
                    user_id=data.user_id,
                    dry_run=data.dry_run,
                    include_published=data.include_published,
                ),
                start_to_close_timeout=timedelta(hours=24),
                retry_policy=retry_policy,
            )
            uploads.append(upload_result)
            for counter, count in (upload_result.get('stats') or {}).items():
                totals[counter] = totals.get(counter, 0) + count

        return {
            'dry_run': data.dry_run,
            'uploads': uploads,
            'totals': totals,
        }
