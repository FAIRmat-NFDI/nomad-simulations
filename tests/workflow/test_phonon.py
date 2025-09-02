from nomad.datamodel.metainfo.workflow import Link

from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.workflow.phonon import (
    Phonon,
    PhononModel,
    PhononResults,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestPhonon:
    def test_inputs_outputs(self, logger, archive):
        archive.data.model_system = [ModelSystem()]
        archive.data.outputs = [Outputs()]
        workflow = Phonon(
            inputs=[Link(section=archive.data.model_system[0])],
            tasks=[
                SinglePoint(),
                SinglePoint(outputs=[Link(section=archive.data.outputs[0])]),
            ],
        )
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, PhononModel)
        assert isinstance(workflow.results, PhononResults)
        assert len(workflow.inputs) == 2
        assert workflow.model == workflow.inputs[1].section
        assert len(workflow.outputs) == 2
        assert workflow.results == workflow.outputs[0].section
        assert archive.data.model_system[0] in [
            inp.section for inp in workflow.tasks[0].inputs
        ]
        assert archive.data.outputs[0] in [out.section for out in workflow.outputs]

    def test_tasks(self, logger, archive):
        workflow = Phonon(tasks=[SinglePoint(name='FC'), SinglePoint(), SinglePoint()])
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'FC'
        assert workflow.tasks[1].name == 'Force calculation for supercell 1'
        assert workflow.tasks[2].name == 'Phonon calculation'
        phonon_inputs = [inp.section for inp in workflow.tasks[2].inputs]
        for task in workflow.tasks[:-1]:
            assert task in phonon_inputs
