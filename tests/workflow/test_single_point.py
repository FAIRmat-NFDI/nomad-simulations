import pytest

from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.workflow.single_point import (
    SinglePoint,
    SinglePointModel,
    SinglePointResults,
)


class TestSinglePoint:
    def test_inputs_outputs(self, logger, archive):
        archive.data.outputs = [Outputs()]
        archive.data.model_method = [ModelMethod()]
        archive.data.model_system = [ModelSystem()]
        workflow = SinglePoint()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, SinglePointModel)
        assert isinstance(workflow.results, SinglePointResults)
        assert len(workflow.inputs) == 1
        assert workflow.inputs[0].name == 'Single point model'
        assert workflow.inputs[0].section.initial_method == archive.data.model_method[0]
        assert workflow.outputs[0].name == 'Single point results'
        assert len(workflow.outputs) == 2
        assert workflow.outputs[1].section == archive.data.outputs[0]

    @pytest.mark.parametrize('n_outputs', [(1), (2)])
    def test_tasks(self, logger, archive, log_output, n_outputs):
        archive.data.outputs = [Outputs() for _ in range(n_outputs)]
        archive.data.model_system = [ModelSystem()]
        workflow = SinglePoint()
        workflow.normalize(archive, logger)

        if n_outputs > 1:
            assert 'Incorrect number of tasks found.' in log_output.entries[0]['event']
        else:
            assert len(workflow.tasks) == 1
            assert workflow.tasks[0].name == 'Calculation'
            assert workflow.model in [inp.section for inp in workflow.tasks[0].inputs]
            assert archive.data.outputs[0] in [
                out.section for out in workflow.tasks[0].outputs
            ]
