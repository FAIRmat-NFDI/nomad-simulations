from nomad_simulations.schema_packages.model_method import OrbitalLocalization
from nomad_simulations.schema_packages.workflow.beyond_dft import BeyondDFTWorkflow
from nomad_simulations.schema_packages.workflow.coupled_cluster import (
    DFTLocalCCMethod,
    DFTLocalCCResults,
    DFTLocalCCWorkflow,
    HFCCMethod,
    HFCCResults,
    HFCCWorkflow,
    HFLocalCCMethod,
    HFLocalCCResults,
    HFLocalCCWorkflow,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestHFCCWorkflow:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = HFCCWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.method, HFCCMethod)
        assert isinstance(workflow.results, HFCCResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'HF+CC workflow parameters'
        assert workflow.outputs[0].name == 'HF+CC workflow results'
        assert 'Incorrect number of tasks found.' in log_output.entries[0]['event']

    def test_tasks(self, logger, archive):
        workflow = HFCCWorkflow(tasks=[SinglePoint(), SinglePoint()])
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'HF'
        assert workflow.tasks[1].name == 'CC'
        assert workflow.method in [inp.section for inp in workflow.tasks[0].inputs]
        assert workflow.tasks[0] in [inp.section for inp in workflow.tasks[1].inputs]


class TestDFTLocalCCWorkflow:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = DFTLocalCCWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.method, DFTLocalCCMethod)
        assert isinstance(workflow.results, DFTLocalCCResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'DFT-reference local-CC workflow parameters'
        assert workflow.outputs[0].name == 'DFT-reference local-CC workflow results'
        assert 'Incorrect number of tasks found.' in log_output.entries[0]['event']

    def test_not_a_beyond_dft_workflow(self):
        assert not issubclass(DFTLocalCCWorkflow, BeyondDFTWorkflow)

    def test_method_stores_orbital_localization(self):
        localization = OrbitalLocalization(method='Pipek-Mezey')
        method = DFTLocalCCMethod(orbital_localization=localization)

        assert method.orbital_localization is localization

    def test_tasks(self, logger, archive):
        workflow = DFTLocalCCWorkflow(
            tasks=[SinglePoint(), SinglePoint(), SinglePoint()]
        )
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'DFT'
        assert workflow.tasks[1].name == 'Orbital localization'
        assert workflow.tasks[2].name == 'Local CC'
        assert workflow.tasks[0] in [inp.section for inp in workflow.tasks[1].inputs]
        assert workflow.tasks[1] in [inp.section for inp in workflow.tasks[2].inputs]

    def test_two_task_workflow_is_invalid(self, logger, archive, log_output):
        workflow = DFTLocalCCWorkflow(tasks=[SinglePoint(), SinglePoint()])
        workflow.normalize(archive, logger)

        assert workflow.tasks[0].name == 'DFT'
        assert workflow.tasks[1].name != 'Local CC'
        assert any(
            entry['event'] == 'Incorrect number of tasks found.'
            for entry in log_output.entries
        )


class TestHFLocalCCWorkflow:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = HFLocalCCWorkflow()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.method, HFLocalCCMethod)
        assert isinstance(workflow.results, HFLocalCCResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'HF+local-CC workflow parameters'
        assert workflow.outputs[0].name == 'HF+local-CC workflow results'
        assert 'Incorrect number of tasks found.' in log_output.entries[0]['event']

    def test_method_stores_orbital_localization(self):
        localization = OrbitalLocalization(method='Foster-Boys')
        method = HFLocalCCMethod(orbital_localization=localization)

        assert method.orbital_localization is localization

    def test_tasks(self, logger, archive):
        workflow = HFLocalCCWorkflow(
            tasks=[SinglePoint(), SinglePoint(), SinglePoint()]
        )
        workflow.normalize(archive, logger)
        assert workflow.tasks[0].name == 'HF'
        assert workflow.tasks[1].name == 'Orbital localization'
        assert workflow.tasks[2].name == 'Local CC'
        assert workflow.tasks[0] in [inp.section for inp in workflow.tasks[1].inputs]
        assert workflow.tasks[1] in [inp.section for inp in workflow.tasks[2].inputs]

    def test_two_task_workflow_is_invalid(self, logger, archive, log_output):
        workflow = HFLocalCCWorkflow(tasks=[SinglePoint(), SinglePoint()])
        workflow.normalize(archive, logger)

        assert workflow.tasks[0].name == 'HF'
        assert workflow.tasks[1].name != 'Local CC'
        assert any(
            entry['event'] == 'Incorrect number of tasks found.'
            for entry in log_output.entries
        )
