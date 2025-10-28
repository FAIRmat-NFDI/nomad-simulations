from nomad_simulations.schema_packages.workflow.photon_polarization import (
    PhotonPolarizationModel,
    PhotonPolarizationResults,
    PhotonPolarizationWorkflow,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestPhotonPolarizationWorkflow:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = PhotonPolarizationWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, PhotonPolarizationModel)
        assert isinstance(workflow.results, PhotonPolarizationResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'Photon polarization workflow parameters'
        assert workflow.outputs[0].name == 'Photon polarization workflow results'
        assert log_output.entries[0]['event'] == 'Incorrect number of tasks found.'

    def test_tasks(self, logger, archive):
        workflow = PhotonPolarizationWorkflow(tasks=[SinglePoint(), SinglePoint()])
        workflow.normalize(archive, logger)
        for task in workflow.tasks:
            assert workflow.inputs[0].section in [inp.section for inp in task.inputs]
