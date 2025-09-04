from nomad.datamodel.metainfo.workflow import Link

from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.workflow.elastic import (
    Elastic,
    ElasticModel,
    ElasticResults,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestElastic:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = Elastic()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, ElasticModel)
        assert isinstance(workflow.results, ElasticResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'Elastic model'
        assert workflow.inputs[0].section == workflow.model
        assert workflow.outputs[0].name == 'Elastic results'
        assert workflow.outputs[0].section == workflow.results

    def test_tasks(self, logger, archive):
        archive.data.outputs = [Outputs()]
        workflow = Elastic(
            tasks=[
                SinglePoint(),
                SinglePoint(),
                SinglePoint(outputs=[Link(section=archive.data.outputs[0])]),
            ]
        )
        workflow.normalize(archive, logger)
        for n, task in enumerate(workflow.tasks[:-1]):
            assert task.name == f'Deformation calculation for supercell {n}'
            assert workflow.model in [inp.section for inp in task.inputs]
            assert workflow.inputs[0] in task.inputs
        assert workflow.tasks[-1].name == 'Elastic calculation'
        assert archive.data.outputs[0] in [out.section for out in workflow.outputs]
