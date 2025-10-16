from nomad_simulations.schema_packages.workflow.single_point import SinglePoint
from nomad_simulations.schema_packages.workflow.thermodynamics import (
    Thermodynamics,
    ThermodynamicsModel,
    ThermodynamicsResults,
)


class TestThermodynamics:
    def test_inputs_outputs(self, archive, logger):
        workflow = Thermodynamics()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, ThermodynamicsModel)
        assert isinstance(workflow.results, ThermodynamicsResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'Thermodynamics model'
        assert workflow.outputs[0].name == 'Thermodynamics results'
