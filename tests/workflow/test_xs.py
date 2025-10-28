import pytest

from nomad_simulations.schema_packages.workflow.photon_polarization import (
    PhotonPolarizationWorkflow,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint
from nomad_simulations.schema_packages.workflow.xs import XSModel, XSResults, XSWorkflow


class TestXSWorkflow:
    def test_inputs_outputs(self, archive, logger, log_output):
        workflow = XSWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, XSModel)
        assert isinstance(workflow.results, XSResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'XS workflow parameters'

    @pytest.mark.parametrize(
        'tasks, names',
        [
            (
                [SinglePoint(name='GS'), SinglePoint(), PhotonPolarizationWorkflow()],
                ['GS', 'GW', 'PhotonPolarization'],
            ),
            (
                [SinglePoint(), PhotonPolarizationWorkflow()],
                ['DFT', 'PhotonPolarization'],
            ),
        ],
    )
    def test_tasks(self, archive, logger, tasks, names):
        workflow = XSWorkflow(tasks=tasks)
        workflow.normalize(archive, logger)
        for n, name in enumerate(names):
            assert workflow.tasks[n].name == name
        for n, task in enumerate(workflow.tasks[:1]):
            assert task in [inp.section for inp in workflow.tasks[n + 1].inputs]
