# tests/schema_packages/workflow/test_coupled_cluster.py

from nomad_simulations.schema_packages.workflow.coupled_cluster import (
    HFCCModel,
    HFCCResults,
    HFCCWorkflow,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestHFCCWorkflow:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = HFCCWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, HFCCModel)
        assert isinstance(workflow.results, HFCCResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'HF+CC workflow parameters'
        assert workflow.outputs[0].name == 'HF+CC workflow results'
        assert 'Incorrect number of tasks found.' in log_output.entries[0]['event']

    def test_tasks(self, logger, archive):
        workflow = HFCCWorkflow(tasks=[SinglePoint(), SinglePoint()])
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'HF'
        assert workflow.tasks[1].name == 'CC'
        assert workflow.model in [inp.section for inp in workflow.tasks[0].inputs]
        assert workflow.tasks[0] in [inp.section for inp in workflow.tasks[1].inputs]
