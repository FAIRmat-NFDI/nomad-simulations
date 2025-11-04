from typing import Optional

import pytest

from nomad_simulations.schema_packages.properties import FermiSurface


class TestFermiSurface:
    """
    Test the `FermiSurface` class defined in `properties/band_structure.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    @pytest.mark.parametrize(
        'n_bands',
        [
            (None),
            (10),
        ],
    )
    def test_default_quantities(self, n_bands: int | None):
        """
        Test the default quantities assigned when creating an instance of the `HoppingMatrix` class.
        """
        fermi_surface = FermiSurface(n_bands=n_bands)
        assert fermi_surface.iri == 'http://fairmat-nfdi.eu/taxonomy/FermiSurface'
