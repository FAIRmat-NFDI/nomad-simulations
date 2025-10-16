from nomad_simulations.schema_packages.workflow.gw import (
    DFTGWModel,
    DFTGWResults,
    DFTGWWorkflow,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestDFTGWWorkflow:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = DFTGWWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, DFTGWModel)
        assert isinstance(workflow.results, DFTGWResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'DFT+GW workflow parameters'
        assert workflow.outputs[0].name == 'DFT+GW workflow results'
        assert 'Incorrect number of tasks found.' in log_output.entries[0]['event']

    def test_tasks(self, logger, archive):
        workflow = DFTGWWorkflow(tasks=[SinglePoint(), SinglePoint()])
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'DFT'
        assert workflow.tasks[1].name == 'GW'
        assert workflow.model in [inp.section for inp in workflow.tasks[0].inputs]
        assert workflow.tasks[0] in [inp.section for inp in workflow.tasks[1].inputs]
