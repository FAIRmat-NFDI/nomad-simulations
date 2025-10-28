from nomad_simulations.schema_packages.workflow.max_ent import (
    DMFTMaxEntWorkflow,
    DMTMaxEntModel,
    DMTMaxEntResults,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestDMFTMaxEntWorkflow:
    def test_inputs_outputs(self, archive, logger, log_output):
        workflow = DMFTMaxEntWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, DMTMaxEntModel)
        assert isinstance(workflow.results, DMTMaxEntResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'DMFT+MaxEnt workflow parameters'
        assert workflow.outputs[0].name == 'DMFT+MaxEnt workflow results'
        assert log_output.entries[0]['event'] == 'Incorrect number of tasks found.'

    def test_tasks(self, archive, logger):
        workflow = DMFTMaxEntWorkflow(tasks=[SinglePoint(name='DMFT'), SinglePoint()])
        workflow.normalize(archive, logger)
        assert workflow.tasks[0] in [inp.section for inp in workflow.tasks[1].inputs]
