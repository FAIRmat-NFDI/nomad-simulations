from typing import Optional

import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.outputs import Outputs
from nomad_simulations.schema_packages.properties import ElectronicBandStructure

from ..conftest import generate_electronic_band_structure
from . import logger


class TestElectronicBandStructure:
    """
    Test the `ElectronicBandStructure` class defined in `properties/band_structure.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    @pytest.mark.parametrize(
        'n_levels',
        [
            (None),
            (10),
        ],
    )
    def test_default_quantities(self, n_levels: int | None):
        """
        Test the default quantities assigned when creating an instance of the `HoppingMatrix` class.
        """
        electronic_band_structure = ElectronicBandStructure(n_levels=n_levels)
        assert (
            electronic_band_structure.iri
            == 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandStructure'
        )

    # @pytest.mark.parametrize(
    #     'occupation, result',
    #     [
    #         (None, False),
    #         ([], False),
    #         ([[2, 2], [0, 0]], False),  # `value` and `occupation` must have same shape
    #         (
    #             [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
    #             True,
    #         ),
    #     ],
    # )
    # def test_validate_occupation(self, occupation: Optional[list], result: bool):
    #     """
    #     Test the `validate_occupation` method.
    #     """
    #     electronic_band_structure = generate_electronic_band_structure(
    #         value=[[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
    #         occupation=occupation,
    #     )
    #     assert electronic_band_structure.validate_occupation(logger) == result
    @pytest.mark.parametrize(
        'occupation, value, result_validation, result',
        [
            (
                None,
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                (),
                (None, None),
            ),
            (
                [[2, 2], [0, 0]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                (),
                (None, None),
            ),  # `value` and `occupation` must have same shape
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                None,
                (),
                (None, None),
            ),
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                True,
                (
                    [
                        -3,
                        -2,
                        -2,
                        -1,
                        0,
                        0,
                        1,
                        1,
                        2,
                        2,
                        3,
                        3,
                        4,
                        4,
                        4,
                        5,
                    ],
                    [
                        2.0,
                        2.0,
                        2.0,
                        2.0,
                        1.5,
                        1.5,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    ],
                ),
            ),
        ],
    )
    def test_order_eigenvalues(
        self,
        occupation: list | None,
        value: list | None,
        result_validation: bool,
        result: tuple[list, list],
    ):
        """
        Test the `order_eigenvalues` method.
        """
        electronic_band_structure = generate_electronic_band_structure(
            value=value,
            occupation=occupation,
        )
        order_result = electronic_band_structure.order_eigenvalues()
        if not order_result:
            assert result_validation == ()  # Empty tuple means validation failed
        else:
            sorted_value, sorted_occupation = order_result
            assert electronic_band_structure.m_cache['sorted_eigenvalues']
            assert (sorted_value.magnitude == result[0]).all()
            assert (sorted_occupation == result[1]).all()

    @pytest.mark.parametrize(
        'occupation, value, highest_occupied, lowest_unoccupied, result',
        [
            # Not possible to resolve `highest_occupied` and `lowest_unoccupied`
            (
                None,
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                None,
                None,
                (None, None),
            ),
            (
                [[2, 2], [0, 0]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                None,
                None,
                (None, None),
            ),  # `value` and `occupation` must have same shape
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                None,
                None,
                None,
                (None, None),
            ),
            # `highest_occupied` and `lowest_unoccupied` are passed to the class
            (
                None,
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                1.0,
                2.0,
                (1.0, 2.0),
            ),
            (
                [[2, 2], [0, 0]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                1.0,
                2.0,
                (1.0, 2.0),
            ),
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                None,
                1.0,
                2.0,
                (1.0, 2.0),
            ),
            # Resolving `highest_occupied` and `lowest_unoccupied` from `value` and `occupation`
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                None,
                None,
                (1.0, 2.0),
            ),
            # Overwritting stored `highest_occupied` and `lowest_unoccupied` from `value` and `occupation`
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                -3.0,
                4.0,
                (1.0, 2.0),
            ),
        ],
    )
    def test_homo_lumo_eigenvalues(
        self,
        occupation: list | None,
        value: list | None,
        highest_occupied: float | None,
        lowest_unoccupied: float | None,
        result: tuple[float | None, float | None],
    ):
        """
        Test the `resolve_homo_lumo_eigenvalues` method.
        """
        electronic_band_structure = generate_electronic_band_structure(
            value=value,
            occupation=occupation,
            highest_occupied=highest_occupied,
            lowest_unoccupied=lowest_unoccupied,
        )
        homo, lumo = electronic_band_structure.resolve_homo_lumo_eigenvalues()
        if homo is not None and lumo is not None:
            assert (homo.magnitude, lumo.magnitude) == result
        else:
            assert (homo, lumo) == result

    @pytest.mark.parametrize(
        'occupation, value, highest_occupied, lowest_unoccupied, band_gap_result',
        [
            # Not possible to resolve `highest_occupied` and `lowest_unoccupied`
            (
                None,
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                None,
                None,
                None,
            ),
            (
                [[2, 2], [0, 0]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                None,
                None,
                None,
            ),  # `value` and `occupation` must have same shape
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                None,
                None,
                None,
                None,
            ),
            # `highest_occupied` and `lowest_unoccupied` are passed to the class
            (
                None,
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                1.0,
                2.0,
                1.0,
            ),
            (
                [[2, 2], [0, 0]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                1.0,
                2.0,
                1.0,
            ),
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                None,
                1.0,
                2.0,
                1.0,
            ),
            # If (lumo - homo) is negative, band_gap_result is 0
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                None,
                3.0,
                2.0,
                0.0,
            ),
            # Resolving `highest_occupied` and `lowest_unoccupied` from `value` and `occupation`
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                None,
                None,
                1.0,
            ),
            # Overwritting stored `highest_occupied` and `lowest_unoccupied` from `value` and `occupation`
            (
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                [[3, -2], [3, 1], [4, -2], [5, -1], [4, 0], [2, 0], [2, 1], [4, -3]],
                -3.0,
                4.0,
                1.0,
            ),
        ],
    )
    def test_extract_band_gap(
        self,
        occupation: list | None,
        value: list | None,
        highest_occupied: float | None,
        lowest_unoccupied: float | None,
        band_gap_result: float | None,
    ):
        """
        Test the `extract_band_gap` method.
        """
        electronic_band_structure = generate_electronic_band_structure(
            value=value,
            occupation=occupation,
            highest_occupied=highest_occupied,
            lowest_unoccupied=lowest_unoccupied,
        )
        band_gap = electronic_band_structure.extract_band_gap()
        if band_gap is not None:
            assert np.isclose(band_gap.value.magnitude, band_gap_result)
        else:
            assert band_gap == band_gap_result

    def test_extract_fermi_surface(self):
        """
        Test the `extract_band_gap` method.
        """
        # ! add test when `FermiSurface` is implemented
        pass

    @pytest.mark.parametrize(
        'reciprocal_lattice_vectors, result',
        [
            (None, None),
            ([], None),
            ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
        ],
    )
    def test_resolve_reciprocal_cell(
        self,
        reciprocal_lattice_vectors: list[list[float]] | None,
        result: list[list[float]] | None,
    ):
        """
        Test the `resolve_reciprocal_cell` method. This is done via the `normalize` function because `reciprocal_cell` is a
        `QuantityReference`, hence we need to assign it.
        """
        electronic_band_structure = generate_electronic_band_structure(
            reciprocal_lattice_vectors=reciprocal_lattice_vectors
        )
        # `normalize()` instead of `resolve_reciprocal_cell()` in order for refs to work
        # reciprocal_cell = electronic_band_structure.resolve_reciprocal_cell()
        electronic_band_structure.normalize(EntryArchive(), logger)
        reciprocal_cell = electronic_band_structure.reciprocal_cell
        if reciprocal_cell is not None:
            assert np.allclose(reciprocal_cell.magnitude, result)
        else:
            assert reciprocal_cell == result
