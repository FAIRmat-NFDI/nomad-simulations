import pytest

from nomad_simulations.actions import legacy_cleanup_action_entry_point
from nomad_simulations.actions.legacy_cleanup.models import (
    CleanupSingleUploadInput,
    LegacyCleanupWorkflowInput,
)


class TestLegacyCleanupWorkflowInput:
    """Input validation for the legacy-cleanup workflow model."""

    @pytest.mark.parametrize(
        'raw, expected',
        [
            (['upload1', 'upload2'], ['upload1', 'upload2']),
            ('upload1, upload2, upload3', ['upload1', 'upload2', 'upload3']),
            ('upload1,,,upload2', ['upload1', 'upload2']),
            (['upload1,upload2', ' ', 'upload3'], ['upload1', 'upload2', 'upload3']),
        ],
    )
    def test_target_upload_ids_parsing(self, raw, expected):
        input_data = LegacyCleanupWorkflowInput(
            user_id='test-user-id', target_upload_ids=raw
        )

        assert input_data.target_upload_ids == expected

    def test_safety_defaults(self):
        input_data = LegacyCleanupWorkflowInput(
            user_id='test-user-id', target_upload_ids=['upload1']
        )

        assert input_data.dry_run is True
        assert input_data.include_published is False
        assert input_data.upload_id is None

    def test_single_upload_input_defaults(self):
        input_data = CleanupSingleUploadInput(
            upload_id='upload1', user_id='test-user-id'
        )

        assert input_data.dry_run is True
        assert input_data.include_published is False


def test_entry_point_wiring():
    """`load()` assembles the Action without needing a Temporal server."""
    from nomad_simulations.actions.legacy_cleanup.activities import cleanup_upload
    from nomad_simulations.actions.legacy_cleanup.workflows import (
        LegacyCleanupWorkflow,
    )

    action = legacy_cleanup_action_entry_point.load()

    assert action.workflow is LegacyCleanupWorkflow
    assert cleanup_upload in action.activities
    assert legacy_cleanup_action_entry_point.name == 'LegacyContributionsCleanupAction'
