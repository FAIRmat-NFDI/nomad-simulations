from types import SimpleNamespace

import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.numerical_settings import (
    EmpiricalDispersionKnob,
    EmpiricalDispersionSettings,
    KLinePath,
    KMesh,
    KSpaceFunctionalities,
    LocalCorrelationThreshold,
    Pseudopotential,
)

from . import logger
from .conftest import generate_k_line_path, generate_k_space_simulation


class TestLocalCorrelationThreshold:
    def test_accepts_dimensionless_threshold(self):
        threshold = LocalCorrelationThreshold(
            name='TCutPNO',
            value=1.0e-7,
            applies_to='local_virtual_space',
        )

        assert threshold.value == pytest.approx(1.0e-7)
        assert threshold.applies_to == 'local_virtual_space'

    def test_accepts_unit_aware_threshold(self):
        threshold = LocalCorrelationThreshold(
            name='DistanceCutoff',
            value=8.0 * ureg.angstrom,
            applies_to='occupied_domain',
        )

        assert threshold.value.to(ureg.angstrom).magnitude == pytest.approx(8.0)
        assert threshold.applies_to == 'occupied_domain'


class TestKSpace:
    """
    Test the `KSpace` class defined in `numerical_settings.py`.
    """

    @pytest.mark.parametrize(
        'system_type, is_representative, reciprocal_lattice_vectors, model_systems, result',
        [
            ('bulk', False, None, 'default', None),
            ('atom', True, None, 'default', None),
            (
                'bulk',
                True,
                [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                'default',
                [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            ),
            # Test None model_systems case
            ('bulk', True, None, None, None),
        ],
    )
    def test_normalize(
        self,
        system_type: str | None,
        is_representative: bool,
        reciprocal_lattice_vectors: list[list[float]] | None,
        model_systems: str | None,
        result: list[list[float]],
    ):
        """
        Test the `normalize` method. This also test the `resolve_reciprocal_lattice_vectors` method.
        """
        simulation = generate_k_space_simulation(
            system_type=system_type,
            is_representative=is_representative,
            reciprocal_lattice_vectors=reciprocal_lattice_vectors,
        )
        k_space = simulation.model_method[0].numerical_settings[0]
        assert k_space.name == 'KSpace'

        # Mock m_xpath to return None if model_systems parameter is None
        if model_systems is None:

            def mock_xpath(path, dict=False):
                return None

            k_space.m_xpath = mock_xpath

        k_space.normalize(EntryArchive(), logger)
        if k_space.reciprocal_lattice_vectors is not None:
            value = k_space.reciprocal_lattice_vectors.to('1/angstrom').magnitude / (
                2 * np.pi
            )
            assert np.allclose(value, result)
        else:
            assert k_space.reciprocal_lattice_vectors == result


class TestKSpaceFunctionalities:
    """
    Test the `KSpaceFunctionalities` class defined in `numerical_settings.py`.
    """

    @pytest.mark.parametrize(
        'reciprocal_lattice_vectors, check_grid, grid, result',
        [
            (None, None, None, False),
            ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], False, None, True),
            ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], True, None, False),
            ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], True, [6, 6, 6, 4], False),
            ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], True, [6, 6, 6], True),
        ],
    )
    def test_validate_reciprocal_lattice_vectors(
        self,
        reciprocal_lattice_vectors: list[list[float]] | None,
        check_grid: bool,
        grid: list[int] | None,
        result: bool,
    ):
        """
        Test the `validate_reciprocal_lattice_vectors` method.
        """
        # Convert raw list data to pint.Quantity if not None
        rlv_quantity = (
            None
            if reciprocal_lattice_vectors is None
            else np.array(reciprocal_lattice_vectors) / ureg.angstrom
        )

        check = KSpaceFunctionalities().validate_reciprocal_lattice_vectors(
            reciprocal_lattice_vectors=rlv_quantity,
            logger=logger,
            check_grid=check_grid,
            grid=grid,
        )
        assert check == result

    @pytest.mark.parametrize(
        'model_systems_input, expected_keys',
        [
            # Valid case: model_systems with proper symmetry
            # SeeKpath may return more detailed k-point labels than ASE
            ('valid', ['Gamma', 'M', 'R', 'X']),
            # None case: model_systems is None
            (None, None),
        ],
    )
    def test_resolve_high_symmetry_points(self, model_systems_input, expected_keys):
        """
        Test the `resolve_high_symmetry_points` method with valid and None model_systems.

        Note: SeeKpath (HPKOT standard) may return more detailed labels than ASE,
        e.g., distinguishing X_1, X_2 for different X-type points in the same structure.
        We test that the essential keys are present.
        """
        if model_systems_input == 'valid':
            # `ModelSystem.normalize()` need to extract `bulk` as a type.
            simulation = generate_k_space_simulation(
                pbc=[True, True, True],
            )
            model_systems = simulation.model_system
            # normalize to extract symmetry
            simulation.model_system[0].normalize(EntryArchive(), logger)
        else:
            model_systems = model_systems_input

        # Testing the functionality method
        high_symmetry_points = KSpaceFunctionalities().resolve_high_symmetry_points(
            model_systems=model_systems, logger=logger
        )

        if expected_keys is None:
            assert high_symmetry_points is None
        else:
            # Check that essential k-point labels are present
            for key in expected_keys:
                assert key in high_symmetry_points or any(
                    k.startswith(key) for k in high_symmetry_points.keys()
                ), f"Expected key '{key}' not found in {list(high_symmetry_points.keys())}"

    def test_resolve_high_symmetry_points_ase_automatic_reordering(self, log_output):
        """
        Test that ASE automatically reorders vectors to satisfy conventions.

        When ASE detects a lattice type, it reorders vectors to satisfy
        crystallographic conventions (e.g., a < b < c for orthorhombic).
        This test verifies that k-points are successfully generated when
        ASE and spglib agree on the lattice type.
        """
        from ase import Atoms
        from ase.cell import Cell

        # Orthorhombic cell - ASE will reorder to satisfy a < b < c
        cell = Cell([[2.0, 0, 0], [0, 1.0, 0], [0, 0, 3.0]])
        atoms = Atoms(
            'Si2', positions=[[0, 0, 0], [1.0, 0.5, 1.5]], cell=cell, pbc=True
        )

        # ASE will detect this as orthorhombic and reorder automatically
        ase_lattice = cell.get_bravais_lattice(eps=3e-3)
        assert type(ase_lattice).__name__ == 'ORC'
        # ASE reorders: a=1.0, b=2.0, c=3.0 (satisfies a < b < c)
        assert ase_lattice.a < ase_lattice.b < ase_lattice.c

        model_system = SimpleNamespace(
            is_representative=True,
            symmetry=SimpleNamespace(
                bravais_lattice='oP'
            ),  # spglib also says orthorhombic
            representations=[SimpleNamespace(name='primitive')],
            to_ase_atoms=lambda representation_index, logger: atoms,
        )

        high_symmetry_points = KSpaceFunctionalities().resolve_high_symmetry_points(
            model_systems=[model_system], logger=logger
        )

        # Should succeed because ASE automatically reorders to satisfy conventions
        assert high_symmetry_points is not None
        assert len(high_symmetry_points) == 8  # Orthorhombic has 8 points

    def test_resolve_high_symmetry_points_consistency_check_with_real_ase(
        self, log_output
    ):
        """
        Integration test with real ASE objects: near-cubic orthorhombic structure.

        When spglib (via MatID) stores 'oP' (orthorhombic primitive) but ASE
        detects cubic symmetry within tolerance, the code should force ASE to use
        orthorhombic lattice class to maintain metadata consistency.

        This test uses real ASE Cell and Atoms objects to verify the actual behavior.
        """
        from ase import Atoms
        from ase.cell import Cell

        # Near-cubic orthorhombic cell that ASE will detect as cubic within eps=3e-3
        # These parameters are within 0.3% of each other
        cell = Cell([[5.0, 0, 0], [0, 5.001, 0], [0, 0, 5.002]])
        atoms = Atoms(
            'Si2', positions=[[0, 0, 0], [2.5, 2.5, 2.5]], cell=cell, pbc=True
        )

        # Verify ASE detects this as cubic
        ase_lattice = cell.get_bravais_lattice(eps=3e-3)
        assert type(ase_lattice).__name__ == 'CUB'

        # Create a model system where spglib (via MatID) has stored 'oP'
        model_system = SimpleNamespace(
            is_representative=True,
            symmetry=SimpleNamespace(bravais_lattice='oP'),  # spglib says orthorhombic
            representations=[SimpleNamespace(name='primitive')],
            to_ase_atoms=lambda representation_index, logger: atoms,
        )

        high_symmetry_points = KSpaceFunctionalities().resolve_high_symmetry_points(
            model_systems=[model_system], logger=logger
        )

        # Should get orthorhombic k-points, not cubic
        assert high_symmetry_points is not None

        # Orthorhombic has 8 high-symmetry points (Gamma, R, S, T, U, X, Y, Z)
        # Cubic has only 4 (Gamma, M, R, X)
        assert len(high_symmetry_points) == 8
        assert 'Gamma' in high_symmetry_points
        assert 'X' in high_symmetry_points
        assert 'Y' in high_symmetry_points
        assert 'Z' in high_symmetry_points

        # Check that a warning was logged about the mismatch
        warning_events = [entry['event'] for entry in log_output.entries]
        # With %s placeholders, check the template and positional args
        assert any(
            'ASE detected %s but spglib says %s' in event for event in warning_events
        )

    def test_resolve_high_symmetry_points_consistency_check_agreement(self, log_output):
        """
        Integration test: when spglib and ASE agree on symmetry, use ASE's object.

        This test verifies that when both spglib and ASE detect the same lattice
        type, the code uses ASE's detected object without forcing instantiation,
        and no mismatch warning is logged.
        """
        from ase import Atoms
        from ase.cell import Cell

        # Clearly cubic cell - both spglib and ASE will agree
        cell = Cell([[5.0, 0, 0], [0, 5.0, 0], [0, 0, 5.0]])
        atoms = Atoms(
            'Si2', positions=[[0, 0, 0], [2.5, 2.5, 2.5]], cell=cell, pbc=True
        )

        # Verify ASE detects cubic
        ase_lattice = cell.get_bravais_lattice(eps=3e-3)
        assert type(ase_lattice).__name__ == 'CUB'

        # Model system where spglib also says cubic
        model_system = SimpleNamespace(
            is_representative=True,
            symmetry=SimpleNamespace(bravais_lattice='cP'),  # Both agree: cubic
            representations=[SimpleNamespace(name='primitive')],
            to_ase_atoms=lambda representation_index, logger: atoms,
        )

        high_symmetry_points = KSpaceFunctionalities().resolve_high_symmetry_points(
            model_systems=[model_system], logger=logger
        )

        # Should get cubic k-points
        assert high_symmetry_points is not None
        assert len(high_symmetry_points) == 4  # Gamma, M, R, X
        assert 'Gamma' in high_symmetry_points
        assert 'M' in high_symmetry_points
        assert 'R' in high_symmetry_points
        assert 'X' in high_symmetry_points

        # Verify no mismatch warning was logged
        warning_events = [entry['event'] for entry in log_output.entries]
        assert not any('ASE detected' in event for event in warning_events)
        assert not any('but spglib says' in event for event in warning_events)

    @pytest.mark.parametrize(
        'pearson, cell_vectors, expected_point_count',
        [
            pytest.param(
                'tP',
                [[4.0, 0, 0], [0, 4.001, 0], [0, 0, 6.0]],
                6,  # Tetragonal: Gamma, A, M, R, X, Z
                id='tetragonal_near_cubic_base',
            ),
            pytest.param(
                'hP',
                [[3.0, 0, 0], [-1.5, 2.598, 0], [0, 0, 5.0]],
                6,  # Hexagonal: Gamma, A, H, K, L, M
                id='hexagonal',
            ),
            pytest.param(
                'oS',
                [[3.0, 0, 0], [0, 4.0, 0], [0, 0, 5.0]],
                None,  # Bug 1: Non-canonical Pearson symbol (oS equivalent to oC)
                id='bug_1_non_canonical_pearson',
            ),
            pytest.param(
                'mP',
                [[3.0, 0, 0], [0, 4.0, 0.2], [0, 0, 5.0]],
                None,  # Bug 2: Monoclinic with alpha≈90°, beta≈87°
                id='bug_2_monoclinic_alpha_90',
            ),
            pytest.param(
                'oP',
                [[4.0, 0, 0], [0, 4.001, 0], [0, 0, 4.002]],
                None,  # Bug 3: Orthorhombic a≈b≈c
                id='bug_3_metrically_cubic',
            ),
        ],
    )
    def test_resolve_high_symmetry_points_consistency_check_parametrized(
        self, pearson, cell_vectors, expected_point_count, log_output
    ):
        """
        Parametrized test for consistency check across different lattice types.
        """
        from ase import Atoms
        from ase.cell import Cell

        cell = Cell(cell_vectors)
        atoms = Atoms(
            'Si2', positions=[[0, 0, 0], [1.0, 1.0, 1.0]], cell=cell, pbc=True
        )

        model_system = SimpleNamespace(
            is_representative=True,
            symmetry=SimpleNamespace(bravais_lattice=pearson),
            representations=[SimpleNamespace(name='primitive')],
            to_ase_atoms=lambda representation_index, logger: atoms,
        )

        high_symmetry_points = KSpaceFunctionalities().resolve_high_symmetry_points(
            model_systems=[model_system], logger=logger
        )

        assert high_symmetry_points is not None
        assert 'Gamma' in high_symmetry_points
        if expected_point_count is not None:
            assert len(high_symmetry_points) == expected_point_count
        else:
            # For bug regression tests: just verify we got points without error
            assert len(high_symmetry_points) >= 4


@pytest.mark.parametrize(
    'subsection_kwargs, subsection_accessor, expected_attrs',
    [
        pytest.param(
            {'grid': [6, 6, 6]},
            lambda k_space: k_space.k_mesh[0],
            ['k_line_density', 'high_symmetry_points'],
            id='KMesh',
        ),
        pytest.param(
            {
                'high_symmetry_path_names': ['Gamma', 'X', 'R'],
                'high_symmetry_path_values': None,
            },
            lambda k_space: k_space.k_line_path,
            ['high_symmetry_path_values'],
            id='KLinePath',
        ),
    ],
)
def test_kspace_subsection_normalization_order(
    subsection_kwargs, subsection_accessor, expected_attrs
):
    """
    Test that KSpace subsections (KMesh and KLinePath) can access
    reciprocal_lattice_vectors even when normalized before their parent KSpace.
    This tests the fix for issue #126.
    """
    # Create a simulation with KSpace subsection and proper lattice vectors
    # Don't pre-set reciprocal_lattice_vectors - let normalization resolve them
    simulation = generate_k_space_simulation(
        system_type='bulk',
        is_representative=True,
        reciprocal_lattice_vectors=None,  # Will be resolved from ModelSystem
        lattice_vectors=[[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]],
        pbc=[True, True, True],
        **subsection_kwargs,
    )

    # Create archive and set simulation as root of the msection hierarchy
    archive = EntryArchive()
    archive.data = simulation

    # Normalize ModelSystem first so it's available for KSpace
    simulation.model_system[0].normalize(archive, logger)

    k_space = simulation.model_method[0].numerical_settings[0]
    subsection = subsection_accessor(k_space)

    # Explicitly normalize subsection before KSpace (simulating NOMAD's subsection-first order)
    # This should trigger the fix where subsection calls k_space.normalize_reciprocal_lattice_vectors()
    subsection.normalize(archive, logger)

    # Verify that reciprocal_lattice_vectors were resolved and are now available in KSpace
    assert k_space.reciprocal_lattice_vectors is not None

    # Verify that subsection successfully accessed them during normalization
    for attr in expected_attrs:
        assert getattr(subsection, attr) is not None
    # Special check for KLinePath length
    if 'high_symmetry_path_values' in expected_attrs:
        assert len(subsection.high_symmetry_path_values) == 3


class TestKMesh:
    """
    Test the `KMesh` class defined in `numerical_settings.py`.
    """

    @pytest.mark.parametrize(
        'center, grid, result_points, result_offset',
        [
            # No `center` and `grid`
            (None, None, None, None),
            # No `grid`
            ('Gamma-centered', None, None, None),
            ('Monkhorst-Pack', None, None, None),
            # `center` is `'Gamma-centered'`
            (
                'Gamma-centered',
                [2, 2, 2],
                [
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 1.0, 1.0],
                    [1.0, 0.0, 0.0],
                    [1.0, 0.0, 1.0],
                    [1.0, 1.0, 0.0],
                    [1.0, 1.0, 1.0],
                ],
                [0.0, 0.0, 0.0],
            ),
            # `center` is `'Monkhorst-Pack'`
            (
                'Monkhorst-Pack',
                [2, 2, 2],
                [
                    [-0.25, -0.25, -0.25],
                    [-0.25, -0.25, 0.25],
                    [-0.25, 0.25, -0.25],
                    [-0.25, 0.25, 0.25],
                    [0.25, -0.25, -0.25],
                    [0.25, -0.25, 0.25],
                    [0.25, 0.25, -0.25],
                    [0.25, 0.25, 0.25],
                ],
                [0.0, 0.0, 0.0],
            ),
            # Invalid `grid`
            ('Monkhorst-Pack', [-2, 2, 2], None, None),
        ],
    )
    def test_resolve_points_and_offset(
        self, center, grid, result_points, result_offset
    ):
        """
        Test the `resolve_points_and_offset` method.
        """
        k_mesh = KMesh(center=center)
        if grid is not None:
            k_mesh.grid = grid
        points, offset = k_mesh.resolve_points_and_offset(logger=logger)
        if points is not None:
            assert np.allclose(points, result_points)
        else:
            assert points == result_points
        if offset is not None:
            assert np.allclose(offset, result_offset)
        else:
            assert offset == result_offset

    @pytest.mark.parametrize(
        'system_type, is_representative, grid, reciprocal_lattice_vectors, result_get_k_line_density, result_k_line_density',
        [
            # No `grid` and `reciprocal_lattice_vectors`
            ('bulk', False, None, None, None, None),
            # No `reciprocal_lattice_vectors`
            ('bulk', False, [6, 6, 6], None, None, None),
            # No `grid`
            ('bulk', False, None, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], None, None),
            # `is_representative` set to False
            (
                'bulk',
                False,
                [6, 6, 6],
                [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                0.954929658,
                None,
            ),
            # `system_type` is not 'bulk'
            (
                'atom',
                True,
                [6, 6, 6],
                [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                0.954929658,
                None,
            ),
            # All parameters are set
            (
                'bulk',
                True,
                [6, 6, 6],
                [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                0.954929658,
                0.954929658,
            ),
        ],
    )
    def test_resolve_k_line_density(
        self,
        system_type: str | None,
        is_representative: bool,
        grid: list[int] | None,
        reciprocal_lattice_vectors: list[list[float]] | None,
        result_get_k_line_density: float | None,
        result_k_line_density: float | None,
    ):
        """
        Test the `resolve_k_line_density` and `get_k_line_density` methods
        """
        simulation = generate_k_space_simulation(
            system_type=system_type,
            is_representative=is_representative,
            reciprocal_lattice_vectors=reciprocal_lattice_vectors,
            grid=grid,
        )
        k_space = simulation.model_method[0].numerical_settings[0]
        reciprocal_lattice_vectors = k_space.reciprocal_lattice_vectors
        k_mesh = k_space.k_mesh[0]
        model_systems = simulation.model_system
        # Applying method `get_k_line_density`
        get_k_line_density_value = k_mesh.get_k_line_density(
            reciprocal_lattice_vectors=reciprocal_lattice_vectors, logger=logger
        )
        if get_k_line_density_value is not None:
            assert np.isclose(
                get_k_line_density_value.to('angstrom').magnitude,
                result_get_k_line_density,
            )
        else:
            assert get_k_line_density_value == result_get_k_line_density
        # Applying method `resolve_k_line_density`
        k_line_density = k_mesh.resolve_k_line_density(
            model_systems=model_systems,
            reciprocal_lattice_vectors=reciprocal_lattice_vectors,
            logger=logger,
        )
        if k_line_density is not None:
            assert np.isclose(
                k_line_density.to('angstrom').magnitude, result_k_line_density
            )
        else:
            assert k_line_density == result_k_line_density


class TestKLinePath:
    """
    Test the `KLinePath` class defined in `numerical_settings.py`.
    """

    @pytest.mark.parametrize(
        'high_symmetry_path_names, high_symmetry_path_values, result',
        [
            (None, None, False),
            (['Gamma', 'X', 'Y'], None, False),
            ([], [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0]], False),
            (['Gamma', 'X', 'Y'], [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0]], True),
        ],
    )
    def test_validate_high_symmetry_path(
        self,
        high_symmetry_path_names: list[str],
        high_symmetry_path_values: list[list[float]],
        result: bool,
    ):
        """
        Test the `validate_high_symmetry_path` method.
        """
        k_line_path = generate_k_line_path(
            high_symmetry_path_names=high_symmetry_path_names,
            high_symmetry_path_values=high_symmetry_path_values,
        )
        assert k_line_path.validate_high_symmetry_path(logger=logger) == result

    @pytest.mark.parametrize(
        'reciprocal_lattice_vectors, high_symmetry_path_names, result',
        [
            (None, None, []),
            ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], None, []),
            (
                [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                ['Gamma', 'X', 'R'],
                [[0, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0.5]],
            ),
        ],
    )
    def test_resolve_high_symmetry_path_values(
        self,
        reciprocal_lattice_vectors: list[list[float]] | None,
        high_symmetry_path_names: list[str],
        result: list[float],
    ):
        """
        Test the `resolve_high_symmetry_path_values` method. Only testing the valid situation in which the `ModelSystem` normalization worked.
        """
        # `ModelSystem.normalize()` need to extract `bulk` as a type.
        simulation = generate_k_space_simulation(
            pbc=[True, True, True],
            reciprocal_lattice_vectors=reciprocal_lattice_vectors,
            high_symmetry_path_names=high_symmetry_path_names,
            high_symmetry_path_values=None,
        )
        model_system = simulation.model_system[0]
        model_system.normalize(EntryArchive(), logger)  # normalize to extract symmetry

        # `KLinePath` can be understood as a `KMeshBase` section
        k_line_path = simulation.model_method[0].numerical_settings[0].k_line_path
        high_symmetry_points_values = k_line_path.resolve_high_symmetry_path_values(
            simulation.model_system, reciprocal_lattice_vectors, logger
        )
        assert high_symmetry_points_values == result

    def test_get_high_symmetry_path_norm(self, k_line_path: KLinePath):
        """
        Test the `get_high_symmetry_path_norm` method.
        """
        rlv = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]) * ureg('1/meter')
        high_symmetry_path_norms = k_line_path.get_high_symmetry_path_norms(
            reciprocal_lattice_vectors=rlv, logger=logger
        )
        hs_points = [0, 0.5, 0.5 + 1 / np.sqrt(2), 1 + 1 / np.sqrt(2)]
        for i, val in enumerate(hs_points):
            assert np.isclose(high_symmetry_path_norms[i].magnitude, val)

    def test_resolve_points(self, k_line_path: KLinePath):
        """
        Test the `resolve_points` method.
        """
        rlv = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]) * ureg('1/meter')
        hs_points = [0, 0.5, 0.5 + 1 / np.sqrt(2), 1 + 1 / np.sqrt(2)]
        # Define paths
        gamma_x = np.linspace(hs_points[0], hs_points[1], num=5)
        x_y = np.linspace(hs_points[1], hs_points[2], num=5)
        y_gamma = np.linspace(hs_points[2], hs_points[3], num=5)
        points_norm = np.concatenate((gamma_x, x_y, y_gamma))
        k_line_path.resolve_points(
            points_norm=points_norm, reciprocal_lattice_vectors=rlv, logger=logger
        )
        assert len(points_norm) == len(k_line_path.points)
        points = np.array(
            [
                [0.0, 0.0, 0.0],  # 'Gamma'
                [0.125, 0.0, 0.0],
                [0.25, 0.0, 0.0],
                [0.375, 0.0, 0.0],
                [0.5, 0.0, 0.0],  # 'X'
                [0.4, 0.1, 0.0],
                [0.3, 0.2, 0.0],
                [0.2, 0.3, 0.0],
                [0.1, 0.4, 0.0],
                [0.0, 0.5, 0.0],  # 'Y'
                [0.0, 0.4, 0.0],
                [0.0, 0.3, 0.0],
                [0.0, 0.2, 0.0],
                [0.0, 0.1, 0.0],
                [0.0, 0.0, 0.0],  # 'Gamma'
            ]
        )
        assert np.allclose(k_line_path.points, points)


class TestEmpiricalDispersionSettings:
    """
    Tests for dispersion numerical settings schema:
      - typed physical constraints via EmpiricalDispersionKnob
      - container section EmpiricalDispersionSettings
    """

    def test_knobs_roundtrip_and_normalize_noop(self):
        """
        Knobs should be storable and survive normalize() unchanged
        (no special normalization is defined currently).
        """
        dns = EmpiricalDispersionSettings(
            include_c8=True,
            include_three_body_atm=False,
            partition_scheme='Hirshfeld',
            density_source='valence-only',
            knobs=[
                EmpiricalDispersionKnob(kind='s6', applies_to='pairwise', value=1.0),
                EmpiricalDispersionKnob(kind='a1', applies_to='pairwise', value=0.40),
                EmpiricalDispersionKnob(kind='a2', applies_to='pairwise', value=4.00),
            ],
        )

        dns.normalize(EntryArchive(), logger=logger)

        assert dns.include_c8 is True
        assert dns.include_three_body_atm is False
        assert dns.partition_scheme == 'Hirshfeld'
        assert dns.density_source == 'valence-only'

        assert dns.knobs is not None
        assert len(dns.knobs) == 3
        assert dns.knobs[0].kind == 's6'
        assert dns.knobs[0].applies_to == 'pairwise'
        assert dns.knobs[0].value == pytest.approx(1.0)

    @pytest.mark.parametrize(
        'include_three_body_atm, include_c8, include_c10, max_order',
        [
            (None, None, None, None),
            (True, None, None, None),
            (False, True, False, 8),
            (True, True, True, 10),
        ],
    )
    def test_switch_fields(
        self, include_three_body_atm, include_c8, include_c10, max_order
    ):
        """
        Basic storage test for the inclusion switches and max_dispersion_order.
        """
        dns = EmpiricalDispersionSettings(
            include_three_body_atm=include_three_body_atm,
            include_c8=include_c8,
            include_c10=include_c10,
            max_dispersion_order=max_order,
        )
        dns.normalize(EntryArchive(), logger=logger)

        assert dns.include_three_body_atm == include_three_body_atm
        assert dns.include_c8 == include_c8
        assert dns.include_c10 == include_c10
        assert dns.max_dispersion_order == max_order

    @pytest.mark.parametrize(
        'partition_scheme, charge_model, density_source',
        [
            (None, None, None),
            ('Hirshfeld', None, None),
            ('Hirshfeld-I', 'EEQ', 'PAW-reconstructed'),
            ('MBIS', 'CM5', 'all-electron'),
            ('MBIS', 'NPA', 'valence-only'),
        ],
    )
    def test_environment_fields(self, partition_scheme, charge_model, density_source):
        """
        Storage test for environment/charge/density-source categorical fields.
        """
        dns = EmpiricalDispersionSettings(
            partition_scheme=partition_scheme,
            charge_model=charge_model,
            density_source=density_source,
        )
        dns.normalize(EntryArchive(), logger=logger)

        assert dns.partition_scheme == partition_scheme
        assert dns.charge_model == charge_model
        assert dns.density_source == density_source

    def test_multiple_knobs_same_kind_allowed(self):
        """
        It should be allowed to store multiple knobs of the same kind if they
        apply to different contributions (or even if not, schema-wise).
        """
        dns = EmpiricalDispersionSettings(
            knobs=[
                EmpiricalDispersionKnob(
                    kind='s9', applies_to='three_body_atm', value=1.0
                ),
                EmpiricalDispersionKnob(kind='s9', applies_to='pairwise', value=0.0),
            ]
        )
        dns.normalize(EntryArchive(), logger=logger)

        assert len(dns.knobs) == 2
        assert dns.knobs[0].kind == 's9'
        assert dns.knobs[0].applies_to == 'three_body_atm'
        assert dns.knobs[1].kind == 's9'
        assert dns.knobs[1].applies_to == 'pairwise'
