from typing import Optional

import pytest

from nomad_simulations.schema_packages.properties import (
    CrystalFieldSplitting,
    HoppingMatrix,
)


class TestHoppingMatrix:
    """
    Test the `HoppingMatrix` class defined in `properties/hopping_matrix.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    @pytest.mark.parametrize(
        'n_orbitals, rank',
        [
            (None, None),
            (3, [3, 3]),
        ],
    )
    def test_default_quantities(self, n_orbitals: int | None, rank: list | None):
        """
        Test the default quantities assigned when creating an instance of the `HoppingMatrix` class.
        """
        hopping_matrix = HoppingMatrix(n_orbitals=n_orbitals)
        assert hopping_matrix.iri == 'http://fairmat-nfdi.eu/taxonomy/HoppingMatrix'


class TestCrystalFieldSplitting:
    """
    Test the `CrystalFieldSplitting` class defined in `properties/hopping_matrix.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    @pytest.mark.parametrize(
        'n_orbitals, rank',
        [
            (None, None),
            (3, [3]),
        ],
    )
    def test_default_quantities(self, n_orbitals: int | None, rank: list | None):
        """
        Test the default quantities assigned when creating an instance of the `CrystalFieldSplitting` class.
        """
        crystal_field = CrystalFieldSplitting(n_orbitals=n_orbitals)
        assert (
            crystal_field.iri == 'http://fairmat-nfdi.eu/taxonomy/CrystalFieldSplitting'
        )
