import pytest
from nomad.units import ureg

from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties.energies import TotalEnergy
from nomad_simulations.schema_packages.workflow.geometry_optimization import (
    GeometryOptimization,
    GeometryOptimizationResults,
)


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
        assert all(
            t.name.startswith('Geometry Optimization') for t in workflow.tasks
        ), 'Task names should follow pattern'
        assert all(len(t.outputs) == 1 for t in workflow.tasks), (
            'Each task should have one output link'
        )
        assert workflow.tasks[0].outputs[0].name == 'Model System', (
            'Output should be linked to Model System'
        )
