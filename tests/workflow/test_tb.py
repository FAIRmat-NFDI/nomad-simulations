from nomad_simulations.schema_packages.workflow.single_point import SinglePoint
from nomad_simulations.schema_packages.workflow.tb import (
    DFTTBMethod,
    DFTTBOutputs,
    DFTTBWorkflow,
)


class TestDFTTBWorkflow:
    def test_inputs_outputs(self, archive, logger, log_output):
        workflow = DFTTBWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, DFTTBMethod)
        assert isinstance(workflow.results, DFTTBOutputs)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'DFT+TB workflow parameters'
        assert workflow.outputs[0].name == 'DFT+TB worklfow results'

    def test_tasks(self, archive, logger):
        workflow = DFTTBWorkflow(tasks=[SinglePoint(name='GS'), SinglePoint()])
        workflow.normalize(archive, logger)
        assert workflow.tasks[1].name == 'TB'
        assert workflow.tasks[0] in [inp.section for inp in workflow.tasks[1].inputs]
