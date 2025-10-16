import pytest

from nomad_simulations.schema_packages.general import ModelMethod, ModelSystem, Outputs
from nomad_simulations.schema_packages.workflow.general import (
    ParallelWorkflow,
    SerialWorkflow,
    SimulationWorkflow,
    SimulationWorkflowModel,
    SimulationWorkflowResults,
)


@pytest.fixture(scope='function')
def workflow():
    return SimulationWorkflow()


@pytest.fixture(scope='function')
def serial_workflow():
    return SerialWorkflow()


@pytest.fixture(scope='function')
def parallel_workflow():
    return ParallelWorkflow()


class TestSimulationWorklow:
    @pytest.mark.parametrize(
        'assigned, expected',
        [('Test workflow', 'Test workflow'), (None, 'SimulationWorkflow')],
    )
    def test_name(self, assigned, expected, logger, archive, workflow):
        workflow.name = assigned
        workflow.normalize(archive, logger)
        assert workflow.name == expected

    def test_inputs(self, logger, archive, workflow):
        archive.data.model_method = [ModelMethod(), ModelMethod()]
        archive.data.model_system = [ModelSystem()]
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, SimulationWorkflowModel)
        assert workflow.inputs[0].name == 'Input model'
        assert len(workflow.inputs) == 1
        assert workflow.model.initial_method == archive.data.model_method[0]
        assert workflow.model.initial_system == archive.data.model_system[0]

    def test_outputs(self, logger, archive, workflow):
        archive.data.outputs = [Outputs(), Outputs()]
        workflow.normalize(archive, logger)
        assert isinstance(workflow.results, SimulationWorkflowResults)
        assert len(workflow.outputs) == 1
        assert workflow.outputs[0].name == 'Output results'
        assert workflow.results.final_outputs == archive.data.outputs[-1]

    @pytest.mark.parametrize(
        'times, linked',
        [
            ([(0, 1), (1, 2), (3, 4)], [(0, 1), (1, 2)]),
            (
                [(0, 1), (0, 2), (2, 3), (2, 4), (4, 5)],
                [(0, 2), (0, 3), (1, 2), (1, 3), (2, 4), (3, 4)],
            ),
            (
                [(0, 1), (0, 1), (0, 2), (3, 4), (4, 5)],
                [(0, 3), (1, 3), (2, 3), (3, 4)],
            ),
            (
                [(0, 1), (1, 2), (1, 3), (3, 4), (3, 5)],
                [(0, 1), (0, 2), (1, 3), (1, 4), (2, 3), (2, 4)],
            ),
            (
                [(4, 5), (0, 1), (2, 3), (1, 2), (2, 4)],
                [(0, 1), (1, 2), (1, 3), (2, 4), (3, 4)],
            ),
        ],
    )
    def test_tasks(self, logger, archive, workflow, times, linked):
        archive.data.model_method.append(ModelMethod())
        archive.data.outputs = [
            Outputs(wall_start=time[0], wall_end=time[1]) for time in times
        ]
        workflow.normalize(archive, logger)
        assert len(workflow.tasks) == len(times)
        for source, target in linked:
            assert workflow.tasks[source] in [
                inp.section for inp in workflow.tasks[target].inputs
            ]


class TestSerialWorkflow:
    n_outputs = 3

    def test_inputs_outputs(self, logger, archive, serial_workflow):
        archive.data.model_method = [ModelMethod()]
        archive.data.outputs = [Outputs() for _ in range(self.n_outputs)]
        serial_workflow.normalize(archive, logger)
        assert len(serial_workflow.inputs) == 1
        assert (
            serial_workflow.inputs[0].section.initial_method
            == archive.data.model_method[0]
        )
        assert len(serial_workflow.outputs) == 2
        assert serial_workflow.outputs[0].name == 'Output results'
        assert (
            serial_workflow.outputs[0].section.final_outputs == archive.data.outputs[-1]
        )
        assert serial_workflow.outputs[1].name == 'Outputs'
        assert serial_workflow.outputs[1].section == archive.data.outputs[-1]

    def test_tasks(self, logger, archive, serial_workflow):
        archive.data.outputs = [Outputs() for _ in range(self.n_outputs)]
        serial_workflow.normalize(archive, logger)
        assert len(serial_workflow.tasks) == self.n_outputs
        for n in range(1, self.n_outputs):
            assert serial_workflow.tasks[n - 1] in [
                inp.section for inp in serial_workflow.tasks[n].inputs
            ]
        for inp in serial_workflow.inputs:
            assert inp in serial_workflow.tasks[0].inputs
        for out in serial_workflow.tasks[-1].outputs:
            assert out in serial_workflow.outputs


class TestParallelWorkflow:
    n_outputs = 3

    def test_inputs_outputs(self, logger, archive, parallel_workflow):
        archive.data.model_system = [ModelSystem()]
        archive.data.outputs = [Outputs() for _ in range(self.n_outputs)]
        parallel_workflow.normalize(archive, logger)
        assert len(parallel_workflow.inputs) == 1
        assert (
            parallel_workflow.inputs[0].section.initial_system
            == archive.data.model_system[0]
        )
        assert len(parallel_workflow.outputs) == self.n_outputs + 1
        assert parallel_workflow.outputs[0].name == 'Output results'
        assert (
            parallel_workflow.outputs[0].section.final_outputs
            == archive.data.outputs[-1]
        )
        for n, output in enumerate(parallel_workflow.outputs[1:]):
            assert output.section == archive.data.outputs[n]

    def test_tasks(self, logger, archive, parallel_workflow):
        archive.data.outputs = [Outputs() for _ in range(self.n_outputs)]
        parallel_workflow.normalize(archive, logger)
        assert len(parallel_workflow.tasks) == self.n_outputs
        for task in parallel_workflow.tasks:
            for inp in task.inputs:
                assert inp in parallel_workflow.inputs
            for out in task.outputs:
                assert out in parallel_workflow.outputs
