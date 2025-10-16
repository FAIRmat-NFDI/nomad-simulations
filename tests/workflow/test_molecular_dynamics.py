from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.workflow.molecular_dynamics import (
    MolecularDynamics,
    MolecularDynamicsModel,
    MolecularDynamicsResults,
)


class TestMolecularDynamics:
    n_outputs = 3

    def test_inputs_outputs(self, logger, archive):
        archive.data.outputs = [Outputs() for _ in range(self.n_outputs)]
        workflow = MolecularDynamics()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, MolecularDynamicsModel)
        assert isinstance(workflow.results, MolecularDynamicsResults)
        assert len(workflow.tasks) == self.n_outputs
        for n, task in enumerate(workflow.tasks):
            assert task.name == f'Step {n}'
