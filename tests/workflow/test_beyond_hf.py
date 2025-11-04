from nomad.datamodel import EntryMetadata
from nomad.datamodel.metainfo.workflow import TaskReference

from nomad_simulations.schema_packages.workflow.beyond_hf import (
    BeyondHFModel,
    BeyondHFResults,
    BeyondHFWorkflow,
)


class TestBeyondHF:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = BeyondHFWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, BeyondHFModel)
        assert isinstance(workflow.results, BeyondHFResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'HF+ workflow parameters'
        assert workflow.outputs[0].name == 'HF+ workflow results'
        assert log_output.entries[0]['event'] == 'Incorrect number of tasks found.'

    # TODO enable once tests with infra is permitted
    def _test_tasks(
        self, logger, archive, upload_data, context, upload_id, main_author
    ):
        archive.metadata = EntryMetadata(upload_id=upload_id, main_author=main_author)
        archive.m_context = context
        workflow = BeyondHFWorkflow()
        # attach workflow to archive inorder for archive resolution to work
        archive.workflow2 = workflow
        workflow.tasks = [
            TaskReference(
                task=f'/uploads/{upload_id}/archive/test_entry_hf#/workflow2'
            ),
            TaskReference(
                task=f'/uploads/{upload_id}/archive/test_entry_single_point#/workflow2'
            ),
        ]
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'HF'
        assert workflow.tasks[0].task in [
            inp.section for inp in workflow.tasks[1].inputs
        ]
