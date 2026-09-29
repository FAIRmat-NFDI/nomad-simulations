import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.properties import ElectronicEigenvalues
from nomad_simulations.schema_packages.variables import KPoints

from ..conftest import K_SAMPLING_POINTS, generate_electronic_eigenvalues
from . import logger


class TestElectronicEigenvalues:
    """
    Test the `ElectronicEigenvalues` class defined in `properties/electronic_eigenvalues.py`.
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
        Test the default quantities assigned when creating an instance of the `ElectronicEigenvalues` class.
        """
        electronic_eigenvalues = ElectronicEigenvalues(n_levels=n_levels)
        assert (
            electronic_eigenvalues.iri
            == 'http://fairmat-nfdi.eu/taxonomy/ElectronicEigenvalues'
        )

    def test_k_points_axis(self):
        """
        Test that the `k_points` axis stores the sampled coordinates directly and carries
        optional integration weights.
        """
        weights = [0.125] * 8
        electronic_eigenvalues = generate_electronic_eigenvalues(weights=weights)
        assert isinstance(electronic_eigenvalues.k_points, KPoints)
        assert np.asarray(electronic_eigenvalues.k_points.points).shape == (8, 3)
        assert np.allclose(electronic_eigenvalues.k_points.weights, weights)

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
        electronic_eigenvalues = generate_electronic_eigenvalues(
            value=value,
            occupation=occupation,
        )
        order_result = electronic_eigenvalues.order_eigenvalues()
        if not order_result:
            assert result_validation == ()  # Empty tuple means validation failed
        else:
            sorted_value, sorted_occupation = order_result
            assert electronic_eigenvalues.m_cache['sorted_eigenvalues']
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
        electronic_eigenvalues = generate_electronic_eigenvalues(
            value=value,
            occupation=occupation,
            highest_occupied=highest_occupied,
            lowest_unoccupied=lowest_unoccupied,
        )
        homo, lumo = electronic_eigenvalues.resolve_homo_lumo_eigenvalues()
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
        electronic_eigenvalues = generate_electronic_eigenvalues(
            value=value,
            occupation=occupation,
            highest_occupied=highest_occupied,
            lowest_unoccupied=lowest_unoccupied,
        )
        band_gap = electronic_eigenvalues.extract_band_gap()
        if band_gap is not None:
            assert np.isclose(band_gap.value.magnitude, band_gap_result)
        else:
            assert band_gap == band_gap_result

    @pytest.mark.parametrize(
        'occupation, spin_channel, result',
        [
            (None, None, False),  # unset occupation
            ([[0, 2], [0, 2]], None, False),  # insulating: filled and empty only
            ([[0, 1.5], [0, 2]], None, True),  # partial occupation
            ([[0, 2], [2, 0]], None, True),  # band crossing: filled and empty per level
            (
                [[0, 1], [0, 1]],
                0,
                False,
            ),  # insulating, spin-resolved (max occupation 1)
            ([[0, 1], [0, 0.5]], 0, True),  # partial occupation, spin-resolved
            ([[0, 1], [0, 1]], None, True),  # 1 is partial when max occupation is 2
        ],
    )
    def test_is_metallic(
        self,
        occupation: list | None,
        spin_channel: int | None,
        result: bool,
    ):
        """
        Test the `is_metallic` occupation-pattern detection.
        """
        electronic_eigenvalues = generate_electronic_eigenvalues(occupation=occupation)
        if spin_channel is not None:
            electronic_eigenvalues.spin_channel = spin_channel
        assert electronic_eigenvalues.is_metallic() == result

    @pytest.mark.parametrize(
        'has_k_points, occupation, expected_homo, expected_lumo, n_gaps',
        [
            # Insulating occupation with a sampling: reference levels and one gap
            (
                True,
                [[0, 2], [0, 2], [0, 2], [0, 2], [0, 2], [0, 2], [0, 2], [0, 2]],
                1.0,
                2.0,
                1,
            ),
            # No `k_points` axis: no derivation at all
            (
                False,
                [[0, 2], [0, 2], [0, 2], [0, 2], [0, 2], [0, 2], [0, 2], [0, 2]],
                None,
                None,
                0,
            ),
            # Metallic occupation pattern: no reference levels, no gap
            (
                True,
                [[0, 2], [0, 1], [0, 2], [0, 2], [0, 1.5], [0, 1.5], [0, 1], [0, 2]],
                None,
                None,
                0,
            ),
        ],
    )
    def test_normalize_gating(
        self,
        has_k_points: bool,
        occupation: list,
        expected_homo: float | None,
        expected_lumo: float | None,
        n_gaps: int,
    ):
        """
        Test that `normalize` derives the reference levels and emits the band gap only for a
        populated `k_points` axis with a non-metallic occupation pattern.
        """
        electronic_eigenvalues = generate_electronic_eigenvalues(
            occupation=occupation,
            k_points=K_SAMPLING_POINTS if has_k_points else None,
        )
        electronic_eigenvalues.normalize(EntryArchive(), logger)
        outputs = electronic_eigenvalues.m_parent
        if expected_homo is None:
            assert electronic_eigenvalues.highest_occupied is None
            assert electronic_eigenvalues.lowest_unoccupied is None
        else:
            assert np.isclose(
                electronic_eigenvalues.highest_occupied.magnitude, expected_homo
            )
            assert np.isclose(
                electronic_eigenvalues.lowest_unoccupied.magnitude, expected_lumo
            )
        assert len(outputs.electronic_band_gaps) == n_gaps
        if n_gaps:
            gap = outputs.electronic_band_gaps[0]
            assert gap.is_derived
            assert np.isclose(gap.value.magnitude, expected_lumo - expected_homo)

    def test_emit_band_gap_idempotency(self):
        """
        Test that re-normalization does not duplicate the emitted band gap.
        """
        electronic_eigenvalues = generate_electronic_eigenvalues(
            occupation=[[0, 2]] * 8,
        )
        archive = EntryArchive()
        electronic_eigenvalues.normalize(archive, logger)
        electronic_eigenvalues.normalize(archive, logger)
        outputs = electronic_eigenvalues.m_parent
        assert len(outputs.electronic_band_gaps) == 1

    def test_extract_fermi_surface(self):
        """
        Test the `extract_fermi_surface` method.
        """
        # ! add test when `FermiSurface` is implemented
        pass
