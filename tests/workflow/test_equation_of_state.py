import numpy as np
import pytest
from nomad.units import ureg

from nomad_simulations.schema_packages.model_system import Cell, ModelSystem
from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties.energies import TotalEnergy
from nomad_simulations.schema_packages.workflow.equation_of_state import (
    FUNCTION_NAMES,
    EquationOfState,
    EquationOfStateModel,
    EquationOfStateResults,
)


class TestEquationOfState:
    def test_inputs_outputs(self, logger, archive, log_output):
        workflow = EquationOfState()
        workflow.normalize(archive, logger)
        assert isinstance(workflow.model, EquationOfStateModel)
        assert isinstance(workflow.results, EquationOfStateResults)
        assert len(workflow.inputs) == 1
        assert len(workflow.outputs) == 1
        assert workflow.inputs[0].name == 'EquationOfState workflow parameters'
        assert workflow.outputs[0].name == 'EquationOfState workflow results'
        assert log_output.entries[0]['event'] == 'Incorrect number of tasks found.'

    @pytest.mark.parametrize(
        'energies, volumes, expected',
        [
            (
                [
                    -7.79764899e-19,
                    -8.18586093e-19,
                    -8.45065510e-19,
                    -8.54267069e-19,
                    -8.68389051e-19,
                    -8.62550424e-19,
                    -8.57757373e-19,
                    -8.69223050e-19,
                    -8.65712609e-19,
                    -8.37491416e-19,
                ],
                [
                    1.54061185e-29,
                    1.64443952e-29,
                    1.75282984e-29,
                    1.80876736e-29,
                    1.98369343e-29,
                    2.23398717e-29,
                    2.29968888e-29,
                    2.04441492e-29,
                    1.92418747e-29,
                    2.50449611e-29,
                ],
                dict(
                    n_points=10,
                    energies=[[4, -8.68389051e-19]],
                    volumes=[[7, 2.04441492e-29]],
                    inconsistent_sizes=False,
                    n_eos_fit=5,
                    eos_fit=[
                        dict(
                            function_name='birch_murnaghan',
                            bulk_modulus=87836876358.25404,
                        ),
                        dict(
                            function_name='pourier_tarantola',
                            fitted_energies=[
                                -7.7979552902520155e-19,
                                -8.185426714929082e-19,
                                -8.4503264240436495e-19,
                                -8.542639697793283e-19,
                                -8.68413767049735e-19,
                                -8.625204277491888e-19,
                                -8.577100144822299e-19,
                                -8.692506353625844e-19,
                                -8.657590037214476e-19,
                                -8.375188329330177e-19,
                            ],
                        ),
                        dict(
                            function_name='vinet',
                            equilibrium_energy=-8.692022014336989e-19,
                        ),
                        dict(
                            function_name='murnaghan',
                            equilibrium_volume=2.0475963394681623e-29,
                        ),
                        dict(
                            function_name='birch_euler', rms_error=0.0005051474157975135
                        ),
                    ],
                ),
            ),
            (
                [
                    -7.79764899e-19,
                    -8.18586093e-19,
                ],
                [
                    1.54061185e-29,
                    1.64443952e-29,
                ],
                dict(
                    n_points=2,
                    energies=[[1, -8.18586093e-19]],
                    volumes=[[1, 1.64443952e-29]],
                    inconsistent_sizes=False,
                    n_eos_fit=0,
                ),
            ),
            (
                [
                    -7.79764899e-19,
                    -8.18586093e-19,
                    -8.45065510e-19,
                ],
                [
                    1.54061185e-29,
                    1.64443952e-29,
                ],
                dict(
                    n_points=3,
                    energies=[[2, -8.45065510e-19]],
                    volumes=[[1, 1.64443952e-29]],
                    inconsistent_sizes=True,
                    n_eos_fit=0,
                ),
            ),
            (
                [-7.79764899e-19],
                [1.54061185e-29, None],
                dict(
                    n_points=1,
                    energies=[[0, -7.79764899e-19]],
                    n_eos_fit=0,
                ),
            ),
            (
                [None, -7.79764899e-19],
                [1.54061185e-29],
                dict(
                    n_points=2,
                    volumes=[[0, 1.54061185e-29]],
                    n_eos_fit=0,
                ),
            ),
        ],
    )
    def test_tasks(
        self, logger, archive, log_output, energies, volumes, expected, approx
    ):
        archive.data.outputs = [
            Outputs(total_energies=[TotalEnergy(value=e)]) for e in energies
        ]
        archive.data.model_system = [
            ModelSystem(
                cell=[Cell(lattice_vectors=(np.eye(3) * v ** (1 / 3.0)) if v else v)]
            )
            for v in volumes
        ]
        workflow = EquationOfState()
        workflow.normalize(archive, logger)
        errors = [entry['event'] for entry in log_output.entries]
        if 'n_points' in expected:
            assert workflow.results.n_points == expected['n_points']
        else:
            assert 'No Outputs found.' in errors
        if 'energies' in expected:
            for n, energy in expected['energies']:
                assert workflow.results.energies[n].magnitude == approx(energy)
        else:
            assert 'Total energy not found in outputs.' in errors
        if 'volumes' in expected:
            for n, volume in expected['volumes']:
                assert workflow.results.volumes[n].magnitude == approx(volume)
        else:
            assert 'Error getting volume from model_system.' in errors
        if expected.get('inconsistent_sizes'):
            assert 'Inconsistent size of energies and volumes.' in errors
        elif expected.get('inconsistent_sizes') is not None:
            assert len(workflow.results.energies) == len(workflow.results.volumes)
        if 0 < expected.get('n_eos_fit', 0) < len(FUNCTION_NAMES):
            assert 'EOS fit unsuccesful.' in errors
        assert len(workflow.results.eos_fit) == expected.get('n_eos_fit', 0)

        for n, expected_fit in enumerate(expected.get('eos_fit', [])):
            assert workflow.results.eos_fit[n].function_name == expected_fit.get(
                'function_name'
            )
            if expected_fit.get('bulk_modulus') is not None:
                assert workflow.results.eos_fit[n].bulk_modulus.magnitude == approx(
                    expected_fit['bulk_modulus']
                )
            if expected_fit.get('equilibrium_energy') is not None:
                assert workflow.results.eos_fit[
                    n
                ].equilibrium_energy.magnitude == approx(
                    expected_fit['equilibrium_energy']
                )
            if expected_fit.get('equilibrium_volume') is not None:
                assert workflow.results.eos_fit[
                    n
                ].equilibrium_volume.magnitude == approx(
                    expected_fit['equilibrium_volume']
                )
            if expected_fit.get('rms_error') is not None:
                assert workflow.results.eos_fit[n].rms_error == approx(
                    expected_fit['rms_error']
                )
            for m, energy in enumerate(expected_fit.get('fitted_energies', [])):
                assert workflow.results.eos_fit[n].fitted_energies[
                    m
                ].magnitude == approx(energy)
