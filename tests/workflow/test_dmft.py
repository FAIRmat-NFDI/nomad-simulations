from nomad.datamodel.metainfo.workflow import Link

from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.workflow.dmft import (
    DFTTBDDMFTModel,
    DFTTBDMFTResults,
    DFTTBDMFTWorkflow,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestDFTTBDMFTWorkflow:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = DFTTBDMFTWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, DFTTBDDMFTModel)
        assert workflow.inputs[0].name == 'DFT+TB+DMFT workflow parameters'
        assert isinstance(workflow.results, DFTTBDMFTResults)
        assert workflow.outputs[0].name == 'DFT+TB+DMFT workflow results'
        assert len(workflow.inputs) == 1
        assert workflow.inputs[0].section == workflow.model
        assert len(workflow.outputs) == 1
        assert workflow.outputs[0].section == workflow.results
        assert log_output.entries[0]['event'] == 'Incorrect number of tasks found.'

    def test_tasks(self, logger, archive):
        archive.data.outputs = [Outputs()]
        workflow = DFTTBDMFTWorkflow(
            tasks=[
                SinglePoint(name='GS'),
                SinglePoint(),
                SinglePoint(outputs=[Link(section=archive.data.outputs[0])]),
            ]
        )
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'GS'
        assert workflow.tasks[1].name == 'TB'
        assert workflow.tasks[2].name == 'DMFT'
        for n, task in enumerate(workflow.tasks[:-1]):
            assert task in [inp.section for inp in workflow.tasks[n + 1].inputs]
        assert archive.data.outputs[0] in [out.section for out in workflow.outputs]
