from nomad.datamodel import EntryMetadata
from nomad.datamodel.metainfo.workflow import TaskReference

from nomad_simulations.schema_packages.workflow.beyond_dft import (
    BeyondDFTModel,
    BeyondDFTResults,
    BeyondDFTWorkflow,
)


class TestBeyondDFT:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = BeyondDFTWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, BeyondDFTModel)
        assert isinstance(workflow.results, BeyondDFTResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'DFT+ workflow parameters'
        assert workflow.outputs[0].name == 'DFT+ workflow results'
        assert log_output.entries[0]['event'] == 'Incorrect number of tasks found.'

    def test_tasks(self, logger, archive, upload_data, context, upload_id, main_author):
        archive.metadata = EntryMetadata(upload_id=upload_id, main_author=main_author)
        archive.m_context = context
        workflow = BeyondDFTWorkflow()
        # attach workflow to archive inorder for archive resolution to work
        archive.workflow2 = workflow
        workflow.tasks = [
            TaskReference(
                task=f'/uploads/{upload_id}/archive/test_entry_dft#/workflow2'
            ),
            TaskReference(
                task=f'/uploads/{upload_id}/archive/test_entry_single_point#/workflow2'
            ),
        ]
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'DFT'
        assert workflow.tasks[0].task in [
            inp.section for inp in workflow.tasks[1].inputs
        ]
