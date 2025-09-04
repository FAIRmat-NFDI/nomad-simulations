import pytest
from nomad.units import ureg

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
