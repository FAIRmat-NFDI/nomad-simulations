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

        entry_ids = {val.mainfile: key for key, val in upload_data.entries.items()}
        dft_archive = archive.m_context.load_archive(
            upload_id, entry_ids['tests/workflow/data/dft.json'], None
        )

        print(dft_archive)
        workflow.tasks = [TaskReference(task=dft_archive.workflow2)]
