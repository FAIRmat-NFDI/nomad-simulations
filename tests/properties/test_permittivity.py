from typing import Optional

import numpy as np
import pytest

from nomad_simulations.schema_packages.properties import Permittivity
from nomad_simulations.schema_packages.variables import Frequency, KMesh, Variables

from ..conftest import generate_k_space_simulation
from . import logger


class TestPermittivity:
    """
    Test the `Permittivity` class defined in `properties/permittivity.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    def test_default_quantities(self):
        """
        Test the default quantities assigned when creating an instance of the `Permittivity` class.
        """
        permittivity = Permittivity()
        assert permittivity.iri == 'http://fairmat-nfdi.eu/taxonomy/Permittivity'

    @pytest.mark.parametrize(
        'kmesh_grid, frequency, result',
        [
            (None, None, 'static'),
            ([], None, 'static'),
            ([3, 3, 3], None, 'static'),
            ([3, 3, 3], Frequency(), 'dynamic'),
        ],
    )
    def test_resolve_type(
        self,
        kmesh_grid: list[int] | None,
        frequency: Variables | None,
        result: str,
    ):
        """
        Test the `resolve_type` method.
        """
        permittivity = Permittivity()

        # Generating `KMesh` numerical settings section
        simulation = generate_k_space_simulation(grid=kmesh_grid)
        k_mesh_settings = simulation.model_method[0].numerical_settings[0].k_mesh[0]
        k_mesh_settings.label = 'q-mesh'
        k_mesh_settings.center = 'Monkhorst-Pack'
        k_mesh_settings.points, _ = k_mesh_settings.resolve_points_and_offset(logger)
        if kmesh_grid is not None and len(kmesh_grid) > 0:
            permittivity.q_mesh = KMesh(points=k_mesh_settings)
        if frequency is not None:
            permittivity.frequencies = frequency
        assert permittivity.resolve_type() == result

    @pytest.mark.parametrize(
        'kmesh_grid, frequencies_points, value, result',
        [
            # Empty case
            (None, None, None, None),
            # No `variables`
            ([], [], np.eye(3) * (1 + 1j), None),
            # If `KMesh` is defined we cannot extract absorption spectra
            (
                [4, 1, 1],
                [],
                np.array([np.eye(3) * k_point * (1 + 1j) for k_point in range(1, 5)]),
                None,
            ),
            # Even if we define `Frequency`, we cannot extract absorption spectra if `value` depends on `KMesh`
            (
                [4, 1, 1],
                [0, 1, 2, 3, 4],
                np.array(
                    [
                        [
                            np.eye(3) * k_point * (1 + 1j)
                            + np.eye(3) * freq_point * 0.5j
                            for freq_point in range(5)
                        ]
                        for k_point in range(1, 5)
                    ]
                ),
                None,
            ),
            # Valid case: `value` does not depend on `KMesh` and we can extract absorption spectra
            (
                [],
                [0, 1, 2, 3, 4],
                np.array([np.eye(3) * freq_point * 0.5j for freq_point in range(5)]),
                [0.0, 0.5, 1.0, 1.5, 2.0],
            ),
        ],
    )
    def test_extract_absorption_spectra(
        self,
        kmesh_grid: list[int] | None,
        frequencies_points: list[float] | None,
        value: np.ndarray | None,
        result: list[float] | None,
    ):
        """
        Test the `extract_absorption_spectra` method. The `result` in the last valid case corresponds to the imaginary part of
        the diagonal of the `Permittivity.value` for each frequency point.
        """
        permittivity = Permittivity()

        # Generating `KMesh` numerical settings section
        simulation = generate_k_space_simulation(grid=kmesh_grid)
        k_mesh_settings = simulation.model_method[0].numerical_settings[0].k_mesh[0]
        k_mesh_settings.label = 'q-mesh'
        k_mesh_settings.center = 'Monkhorst-Pack'
        k_mesh_settings.points, _ = k_mesh_settings.resolve_points_and_offset(logger)
        if kmesh_grid is not None and len(kmesh_grid) > 0:
            kmesh_variables = KMesh(points=k_mesh_settings)
            permittivity.q_mesh = kmesh_variables

        # Adding `Frequency` if defined
        if frequencies_points is not None and len(frequencies_points) > 0:
            frequencies = Frequency(points=frequencies_points)
            permittivity.frequencies = frequencies

        if permittivity.q_mesh is not None or permittivity.frequencies is not None:
            permittivity.value = value

        absorption_spectra = permittivity.extract_absorption_spectra(logger)
        if absorption_spectra is not None:
            assert len(absorption_spectra) == 3
            spectrum = absorption_spectra[1]
            assert spectrum.axis == 'yy'
            if spectrum.frequencies is not None:
                assert len(spectrum.value) == len(permittivity.frequencies.points)
            assert np.allclose(spectrum.value, result)
        else:
            assert absorption_spectra == result
