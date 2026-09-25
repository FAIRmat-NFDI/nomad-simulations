import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.properties.electronic_eigenvalues import (
    ElectronicEigenvalues,
)
from nomad_simulations.schema_packages.variables import KMesh

from . import logger


class TestElectronicEigenvalues:
    """
    Test the `k_mesh` reciprocal-space axis added to `ElectronicEigenvalues` in
    `properties/electronic_eigenvalues.py`.
    """

    def test_k_mesh_subsection_registered(self):
        """The `k_mesh` axis is part of the metainfo definition."""
        eigenvalues = ElectronicEigenvalues()
        assert 'k_mesh' in eigenvalues.m_def.all_sub_sections
        assert eigenvalues.k_mesh is None

    @pytest.mark.parametrize(
        'n_points',
        [None, 1, 260],
    )
    def test_k_mesh_independent_sizing(self, n_points: int | None):
        """
        Each property owns its `k_mesh`; its point count is set on the attached variable and is
        not tied to any shared or global mesh. `n_points=1` covers the FHI-aims default where only
        the Gamma point is printed.
        """
        eigenvalues = ElectronicEigenvalues()
        k_mesh = KMesh()
        if n_points is not None:
            k_mesh.n_points = n_points
        eigenvalues.k_mesh = k_mesh

        assert eigenvalues.k_mesh is not None
        assert eigenvalues.k_mesh.n_points == n_points

    @pytest.mark.parametrize(
        'set_k_mesh',
        [False, True],
    )
    def test_normalize_with_k_mesh(self, set_k_mesh: bool):
        """`normalize` runs whether or not the `k_mesh` axis is populated."""
        eigenvalues = ElectronicEigenvalues()
        if set_k_mesh:
            eigenvalues.k_mesh = KMesh(n_points=1)
        eigenvalues.normalize(archive=EntryArchive(), logger=logger)
