import pytest
from nomad.datamodel.metainfo.workflow import Link, Task
from nomad.units import ureg

from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs, SCFSteps
from nomad_simulations.schema_packages.properties.energies import TotalEnergy
from nomad_simulations.schema_packages.workflow.geometry_optimization import (
    GeometryOptimization,
    GeometryOptimizationResults,
)
from nomad_simulations.schema_packages.workflow.single_point import SinglePoint


class TestGeometryOptimization:
    @pytest.mark.parametrize(
        'energies, ref_energy, ref_energy_diff',
        [
            ([1, 2, 3], 2, 1),
            ([None, 2, 3], None, None),
            ([1, 2, 2], 2, 1),
            ([1, 2e18 * ureg('hartree'), 3], 8.71948944441434, -5.719489444414339),
        ],
    )
    def test_energies(self, logger, archive, energies, ref_energy, ref_energy_diff):
        archive.data.outputs = [
            Outputs(total_energies=[TotalEnergy(value=e)]) for e in energies
        ]
        workflow = GeometryOptimization()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.results, GeometryOptimizationResults)
        if ref_energy:
            assert workflow.results.energies is not None
            assert workflow.results.energies[1].magnitude == ref_energy
        else:
            assert workflow.results.energies is None
        if ref_energy_diff:
            assert workflow.results.final_energy_difference.magnitude == ref_energy_diff
        else:
            assert workflow.results.final_energy_difference is None

    def test_single_step_trajectory_no_energy_diff(self, logger, archive):
        archive.data.outputs = [Outputs(total_energies=[TotalEnergy(value=1)])]
        workflow = GeometryOptimization()
        workflow.normalize(archive, logger)

        assert isinstance(workflow.results, GeometryOptimizationResults)
        assert workflow.results.energies is not None
        assert len(workflow.results.energies) == 1
        assert workflow.results.final_energy_difference is None

    def test_map_tasks_fallback_to_model_system_when_outputs_missing(
        self, logger, archive
    ):
        """Test task creation from model_system when outputs not available (CLI context)."""
        # Set up archive with model_systems but no outputs (simulates CLI/parser context)
        archive.data.model_system = [ModelSystem(), ModelSystem(), ModelSystem()]
        archive.data.outputs = []  # Empty outputs - CLI context scenario

        workflow = GeometryOptimization()
        workflow.normalize(archive, logger)

        # Verify tasks were created from model_system
        assert len(workflow.tasks) == 3, 'Should create 3 tasks from 3 model systems'
        assert all(t.name.startswith('Step') for t in workflow.tasks), (
            'Task names should follow pattern'
        )
        assert all(len(t.outputs) == 1 for t in workflow.tasks), (
            'Each task should have one output link'
        )
        assert workflow.tasks[0].outputs[0].name == 'Model System', (
            'Output should be linked to Model System'
        )

    def test_create_task_for_output_without_scf_steps(self, logger, archive):
        """Test that generic Task is created when output has no SCF steps."""
        workflow = GeometryOptimization()
        output = Outputs()  # No scf_steps attribute

        task = workflow._create_task_for_output(0, output, archive, logger)

        assert isinstance(task, Task)
        assert not isinstance(task, SinglePoint)
        assert task.name == 'Step 0'
        assert len(task.outputs) == 1
        assert task.outputs[0].name == 'Outputs'

    def test_create_task_for_output_with_scf_steps(self, logger, archive):
        """Test that SinglePoint task is created when output has SCF steps."""
        workflow = GeometryOptimization()
        output = Outputs()
        output.scf_steps = SCFSteps()  # Has scf_steps

        task = workflow._create_task_for_output(0, output, archive, logger)

        assert isinstance(task, SinglePoint)
        assert task.name == 'Step 0'
        assert len(task.outputs) == 1
        assert task.outputs[0].name == 'Outputs'

    def test_link_task_by_timing_no_timing_info(self, logger, archive):
        """Test that no linking occurs when timing info is missing."""
        workflow = GeometryOptimization()
        task = Task(name='Test Task')
        output = Outputs()  # No wall_start or wall_end
        outputs = [output]
        tasks = [task]

        parent_n, root_n = workflow._link_task_by_timing(
            task, output, outputs, tasks, 0, 0, 0
        )

        assert len(task.inputs) == 0
        assert parent_n == 0
        assert root_n == 0

    def test_link_task_by_timing_sequential_execution(self, logger, archive):
        """Test task linking when tasks execute sequentially (tstart >= tend)."""
        workflow = GeometryOptimization()

        # Create three outputs with sequential timing (in seconds)
        output0 = Outputs()
        output0.wall_start = 0.0
        output0.wall_end = 600.0  # 10 minutes

        output1 = Outputs()
        output1.wall_start = 600.0  # Starts when output0 ends
        output1.wall_end = 1200.0

        output2 = Outputs()
        output2.wall_start = 1200.0  # Starts when output1 ends
        output2.wall_end = 1800.0

        outputs = [output0, output1, output2]

        task0 = Task(name='Step 0', outputs=[Link(name='Outputs', section=output0)])
        task1 = Task(name='Step 1', outputs=[Link(name='Outputs', section=output1)])
        task2 = Task(name='Step 2', outputs=[Link(name='Outputs', section=output2)])

        tasks = [task0, task1, task2]

        # Link task1 (should link to task0)
        parent_n, root_n = workflow._link_task_by_timing(
            task1, output1, outputs, tasks, 1, 0, 0
        )

        assert len(task1.inputs) == 1
        assert task1.inputs[0].section == task0
        assert parent_n == 1
        assert root_n == 0

        # Link task2 (should link to task1)
        parent_n, root_n = workflow._link_task_by_timing(
            task2, output2, outputs, tasks, 2, parent_n, root_n
        )

        assert len(task2.inputs) == 1
        assert task2.inputs[0].section == task1
        assert parent_n == 2
        assert root_n == 1

    def test_link_task_by_timing_parallel_execution(self, logger, archive):
        """Test task linking when tasks execute in parallel (overlap in time)."""
        workflow = GeometryOptimization()

        # Create outputs with overlapping timing (parallel execution)
        output0 = Outputs()
        output0.wall_start = 0.0
        output0.wall_end = 1200.0  # 20 minutes

        output1 = Outputs()
        output1.wall_start = 300.0  # Starts 5 minutes in, before output0 ends
        output1.wall_end = 900.0

        output2 = Outputs()
        output2.wall_start = 480.0  # Starts 8 minutes in, before output0 ends
        output2.wall_end = 1080.0

        outputs = [output0, output1, output2]

        task0 = Task(name='Step 0', outputs=[Link(name='Outputs', section=output0)])
        task1 = Task(name='Step 1', outputs=[Link(name='Outputs', section=output1)])
        task2 = Task(name='Step 2', outputs=[Link(name='Outputs', section=output2)])

        tasks = [task0, task1, task2]

        # Link task1 (parallel to task0, should link to root)
        parent_n, root_n = workflow._link_task_by_timing(
            task1, output1, outputs, tasks, 1, 0, 0
        )

        assert len(task1.inputs) == 0  # Links to empty range [0:0]
        assert parent_n == 0
        assert root_n == 0

        # Link task2 (parallel to task0, should link to root)
        parent_n, root_n = workflow._link_task_by_timing(
            task2, output2, outputs, tasks, 2, parent_n, root_n
        )

        assert len(task2.inputs) == 0  # Links to empty range [0:0]

    def test_map_tasks_from_model_system(self, logger, archive):
        """Test _map_tasks_from_model_system helper method directly."""
        archive.data.model_system = [ModelSystem(), ModelSystem()]
        workflow = GeometryOptimization()

        workflow._map_tasks_from_model_system(archive, logger)

        assert len(workflow.tasks) == 2
        assert all(t.name.startswith('Step') for t in workflow.tasks)
        assert all(t.outputs[0].name == 'Model System' for t in workflow.tasks)

    def test_map_tasks_from_outputs(self, logger, archive):
        """Test _map_tasks_from_outputs helper method directly."""
        # Create outputs with timing (in seconds)
        output0 = Outputs()
        output0.wall_start = 0.0
        output0.wall_end = 600.0  # 10 minutes

        output1 = Outputs()
        output1.wall_start = 600.0  # Starts when output0 ends
        output1.wall_end = 1200.0

        archive.data.outputs = [output0, output1]
        workflow = GeometryOptimization()

        workflow._map_tasks_from_outputs(archive, logger)

        assert len(workflow.tasks) == 2
        assert workflow.tasks[0].name == 'Step 0'
        assert workflow.tasks[1].name == 'Step 1'
        # Task 1 should be linked to Task 0
        assert len(workflow.tasks[1].inputs) == 1
        assert workflow.tasks[1].inputs[0].section == workflow.tasks[0]
