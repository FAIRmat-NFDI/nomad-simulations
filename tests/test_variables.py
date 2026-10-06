import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.variables import KLinePath, KPoints, Variables

from . import logger


class TestVariables:
    """
    Test the `Variables` class defined in `variables.py`.
    """

    @pytest.mark.parametrize(
        'n_points, points, result',
        [
            (3, [-1, 0, 1], 3),
            (5, [-1, 0, 1], 3),
            (None, [-1, 0, 1], 3),
            (4, None, 4),
            (4, [], 4),
        ],
    )
    def test_normalize(self, n_points: int, points: list, result: int):
        """
        Test the `normalize` and `get_n_points` methods.
        """
        variable = Variables(
            name='variable_1',
            n_points=n_points,
            points=points,
        )
        assert variable.get_n_points(logger=logger) == result
        variable.normalize(EntryArchive(), logger)
        assert variable.n_points == result

    def test_name_setting_during_normalization(self):
        """
        Test that the name is set during normalization for Variables.
        """
        variable = Variables()
        variable.normalize(EntryArchive(), logger)
        assert variable.name == 'Variables'


class TestKPoints:
    """
    Test the `KPoints` and `KLinePath` variables defined in `variables.py`.
    """

    @pytest.mark.parametrize(
        'points, weights, n_points',
        [
            ([[0, 0, 0], [0.5, 0.5, 0.5]], None, 2),  # weights are optional
            ([[0, 0, 0], [0.5, 0.5, 0.5]], [0.25, 0.75], 2),
            ([[0, 0, 0], [0.5, 0, 0], [0, 0, 0]], None, 3),  # duplicates are allowed
        ],
    )
    def test_direct_storage(
        self,
        points: list[list[float]],
        weights: list[float] | None,
        n_points: int,
    ):
        """
        Test that `KPoints` stores the sampled coordinates directly and resolves `n_points`.
        """
        k_points = KPoints(points=points)
        if weights is not None:
            k_points.weights = weights
        k_points.normalize(EntryArchive(), logger)
        assert k_points.n_points == n_points
        assert np.asarray(k_points.points).shape == (n_points, 3)
        if weights is not None:
            assert np.allclose(k_points.weights, weights)

    def test_k_line_path_inherits_k_points(self):
        """
        Test that `KLinePath` subclasses `KPoints`, inheriting the direct point storage, and
        adds the high-symmetry segment structure.
        """
        assert issubclass(KLinePath, KPoints)
        k_line_path = KLinePath(
            points=[[0, 0, 0], [0.25, 0, 0], [0.5, 0, 0], [0.5, 0.25, 0.25]],
            high_symmetry_labels=['Γ', 'X', 'R'],
            high_symmetry_indices=[0, 2, 3],
        )
        k_line_path.normalize(EntryArchive(), logger)
        assert k_line_path.n_points == 4
        assert k_line_path.name == 'KLinePath'
        assert list(k_line_path.high_symmetry_labels) == ['Γ', 'X', 'R']
        assert list(k_line_path.high_symmetry_indices) == [0, 2, 3]
        # A path carries no Brillouin-zone integration measure
        assert k_line_path.weights is None
