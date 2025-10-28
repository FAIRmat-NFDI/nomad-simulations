from typing import Optional, Union

import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.properties import ElectronicBandGap
from nomad_simulations.schema_packages.variables import Temperature

from . import logger


class TestElectronicBandGap:
    """
    Test the `ElectronicBandGap` class defined in `properties/band_gap.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    def test_default_quantities(self):
        """
        Test the default quantities assigned when creating an instance of the `ElectronicBandGap` class.
        """
        electronic_band_gap = ElectronicBandGap()
        assert (
            electronic_band_gap.iri
            == 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandGap'
        )

    @pytest.mark.parametrize(
        'momentum_transfer, type, result',
        [
            (None, None, None),
            (None, 'direct', 'direct'),
            (None, 'indirect', 'indirect'),
            ([[0, 0, 0]], None, None),
            ([[0, 0, 0]], 'direct', None),
            ([[0, 0, 0]], 'indirect', None),
            ([[0, 0, 0], [0, 0, 0]], None, 'direct'),
            ([[0, 0, 0], [0, 0, 0]], 'direct', 'direct'),
            ([[0, 0, 0], [0, 0, 0]], 'indirect', 'direct'),
            ([[0, 0, 0], [0.5, 0.5, 0.5]], None, 'indirect'),
            ([[0, 0, 0], [0.5, 0.5, 0.5]], 'direct', 'indirect'),
            ([[0, 0, 0], [0.5, 0.5, 0.5]], 'indirect', 'indirect'),
        ],
    )
    def test_resolve_type(
        self, momentum_transfer: list[float] | None, type: str, result: str | None
    ):
        """
        Test the `resolve_type` method.
        """
        electronic_band_gap = ElectronicBandGap(
            momentum_transfer=momentum_transfer,
            type=type,
        )
        assert electronic_band_gap.resolve_type(logger=logger) == result

    def test_normalize(self):
        """
        Test the `normalize` method for two different ElectronicBandGap instantiations, one with a scalar
        `value` and another with a temperature-dependent `value`
        """
        scalar_band_gap = ElectronicBandGap(type='direct')
        scalar_band_gap.value = 1.0 * ureg.joule
        scalar_band_gap.normalize(EntryArchive(), logger)
        assert scalar_band_gap.type == 'direct'
        assert np.isclose(scalar_band_gap.value.magnitude, 1.0)

        # t_dependent_band_gap = ElectronicBandGap(
        #     variables=[Temperature(points=[0, 10, 20, 30] * ureg.kelvin)],
        #     type='direct',
        # )
        # t_dependent_band_gap.value = [1.0, 2.0, 3.0, 4.0] * ureg.joule
        # t_dependent_band_gap.normalize(EntryArchive(), logger)
        # assert t_dependent_band_gap.type == 'direct'
        # assert (
        #     np.isclose(t_dependent_band_gap.value.magnitude, [1.0, 2.0, 3.0, 4.0])
        # ).all()
