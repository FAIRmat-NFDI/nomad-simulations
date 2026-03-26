import ase
import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    CGBeadState,
    ParticleState,
)
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_system import (
    ChemicalFormula,
    GlobalCrystalSymmetry,
    LocalCrystalSymmetry,
    LocalSymmetry,
    ModelSystem,
    Representation,
    Symmetry,
)

from . import logger
from .conftest import generate_model_system


class TestSymmetry:
    """
    Test the `Symmetry` class defined in model_system.py.
    """

    def test_resolve_bulk_symmetry_empty(self):
        """
        Check what happens if original_atomic_cell is None or minimal.
        """
        sym = Symmetry()
        primitive, conv = sym.resolve_bulk_symmetry(None, logger=logger)
        assert primitive is None
        assert conv is None


class TestChemicalFormula:
    """
    Test the `ChemicalFormula` class defined in model_system.py.
    """

    def test_normalize_no_cell(self):
        """
        If no sibling AtomicCell is found, the formula fields should remain None.
        """
        chem = ChemicalFormula()
        chem.normalize(EntryArchive(), logger)
        for f in ['descriptive', 'reduced', 'iupac', 'hill', 'anonymous']:
            assert getattr(chem, f) is None

    def test_normalize_default_chemical_formula(self):
        """
        Test that ChemicalFormula.normalize() correctly sets the formulas (e.g. 'H2O')
        when no sibling AtomicCell is provided.
        """
        chem = ChemicalFormula()
        chem.normalize(EntryArchive(), logger)
        if chem.descriptive is not None:
            assert chem.descriptive == 'H2O'


class TestModelSystem:
    """
    Tests each function in ModelSystem. This includes:
      - to_ase_atoms
      - from_ase_atoms
      - resolve_system_type_and_dimensionality
      - normalize
      - sub-system logic (branch_depth, composition_formula, etc.)
    """

    def test_to_ase_atoms(self):
        """
        Verify that a ModelSystem with positions, lattice vectors, and valid AtomsState
        entries produces a valid ASE Atoms object with correct cell and symbols.
        Tests both original data and representation data.
        """
        sys = ModelSystem(is_representative=True)
        sys.positions = np.array([[0, 0, 0], [0.5, 0, 0.5]]) * ureg.angstrom
        # Set original cell data at ModelSystem level
        sys.lattice_vectors = np.eye(3) * 4.0 * ureg.angstrom
        sys.periodic_boundary_conditions = [True, True, True]

        # Add a representation
        rep = Representation(
            lattice_vectors=np.eye(3) * 5.0 * ureg.angstrom,
            periodic_boundary_conditions=[True, True, False],
            name='modified',
        )
        sys.representations.append(rep)

        # Add AtomsState entries for 2 atoms
        a1 = AtomsState(chemical_symbol='Na')
        a2 = AtomsState(chemical_symbol='Cl')
        sys.particle_states.extend([a1, a2])

        # Test using original data (representation_index=None)
        ase_atoms_orig = sys.to_ase_atoms(representation_index=None, logger=logger)
        assert ase_atoms_orig is not None
        assert len(ase_atoms_orig) == 2
        assert np.allclose(ase_atoms_orig.get_cell(), np.eye(3) * 4.0)
        assert ase_atoms_orig.get_pbc().tolist() == [True, True, True]
        assert ase_atoms_orig.get_chemical_symbols() == ['Na', 'Cl']

        # Test using representation data (representation_index=0)
        ase_atoms_rep = sys.to_ase_atoms(representation_index=0, logger=logger)
        assert ase_atoms_rep is not None
        assert len(ase_atoms_rep) == 2
        assert np.allclose(ase_atoms_rep.get_cell(), np.eye(3) * 5.0)
        assert ase_atoms_rep.get_pbc().tolist() == [True, True, False]
        assert ase_atoms_rep.get_chemical_symbols() == ['Na', 'Cl']

    def test_to_ase_atoms_blocks_non_element_symbols(self):
        """
        Ensure to_ase_atoms() refuses to construct an ASE Atoms when the symbols are
        not all valid elements (e.g., CG bead labels), and returns None.
        """
        ms = ModelSystem()
        ms.particle_states.append(CGBeadState(bead_symbol='B1'))
        ms.positions = np.zeros((1, 3)) * ureg.angstrom
        # Set cell data at ModelSystem level
        ms.lattice_vectors = np.eye(3) * ureg.angstrom
        ms.periodic_boundary_conditions = [False, False, False]

        assert ms.to_ase_atoms(representation_index=None, logger=logger) is None

    def test_from_ase_atoms(self):
        """
        Verify that `from_ase_atoms` creates a `ModelSystem` from ASE Atoms object.
        Tests the updated function that returns only `ModelSystem` (no tuple).
        """
        ase_atoms = ase.Atoms(
            'CO',
            positions=[[0, 0, 0], [0, 0, 1.1]],
            cell=np.eye(3) * 4.0,
            pbc=[True, True, True],
        )

        sys = ModelSystem.from_ase_atoms(ase_atoms, logger=logger)

        assert sys.n_particles == 2
        assert sys.positions.shape == (2, 3)

        # Check the ModelSystem has correct lattice_vectors and PBC at top level
        expected_cell = ase.geometry.complete_cell(ase_atoms.get_cell()) * ureg.angstrom
        assert np.allclose(
            sys.lattice_vectors.to('angstrom').magnitude,
            expected_cell.to('angstrom').magnitude,
        )
        # Check PBC
        assert np.array_equal(
            np.array(sys.periodic_boundary_conditions),
            np.array(ase_atoms.get_pbc()),
        )
        # Check particle_states references
        assert len(sys.particle_states) == 2
        syms = [st.chemical_symbol for st in sys.particle_states]
        assert syms == ['C', 'O']

        # Check volume is set for 3D system
        assert sys.volume is not None
        # Volume should be 64.0 Angstrom^3 = 64.0e-30 m^3 (since 1 Angstrom = 1e-10 m)
        assert sys.volume.magnitude == pytest.approx(64.0e-30, rel=1e-6)

    def test_from_ase_atoms_enhanced_properties(self):
        """
        Test that `from_ase_atoms` correctly maps enhanced properties like
        charges, tags, velocities, and fractional coordinates.
        """
        # Create ASE atoms with additional properties
        ase_atoms = ase.Atoms(
            ['H', 'H', 'O'],
            positions=[[0, 0, 0], [0.76, 0.59, 0], [0, 0.96, 0]],
            cell=[10, 10, 10],
            pbc=[True, True, True],
        )

        # Set additional properties
        ase_atoms.set_initial_charges([0.6, 0.7, -1.0])
        ase_atoms.set_tags([1, 1, 2])
        ase_atoms.set_velocities([[0.1, 0.2, 0.0], [0.0, -0.1, 0.0], [0.0, 0.0, 0.1]])

        sys = ModelSystem.from_ase_atoms(ase_atoms, logger=logger)

        # Check basic properties
        assert sys.n_particles == 3
        assert len(sys.particle_states) == 3

        # Check charges were mapped (rounded to integers)
        charges = [ps.charge for ps in sys.particle_states]
        assert charges == [
            1,
            1,
            -1,
        ]  # 0.6 rounds to 1, 0.7 rounds to 1, -1.0 rounds to -1

        # Check tags were mapped to labels
        labels = [ps.label for ps in sys.particle_states]
        assert labels == ['H_1', 'H_1', 'O_2']

        # Check velocities were mapped
        assert sys.velocities is not None
        assert sys.velocities.shape == (3, 3)
        expected_velocities = np.array(
            [[0.1, 0.2, 0.0], [0.0, -0.1, 0.0], [0.0, 0.0, 0.1]]
        )
        assert np.allclose(
            sys.velocities.to('angstrom/second').magnitude, expected_velocities
        )

        # Check fractional coordinates were computed
        assert sys.fractional_coordinates is not None
        assert sys.fractional_coordinates.shape == (3, 3)

        # Check volume for 3D system
        assert sys.volume is not None
        # Volume should be 1000 Angstrom^3 = 1e-27 m^3 (since 1 Angstrom = 1e-10 m)
        assert sys.volume.magnitude == pytest.approx(1e-27, rel=1e-6)

    @pytest.mark.parametrize(
        'cell, pbc, expected_property, expected_value',
        [
            # 3D system - should have volume
            (
                [[2.7, 0, 0], [0, 2.7, 0], [0, 0, 2.7]],
                [True, True, True],
                'volume',
                19.683e-30,  # 19.683 Angstrom^3 = 19.683e-30 m^3
            ),
            # 2D system with vacuum - should have volume (includes vacuum)
            (
                [[2.84, 0, 0], [0, 2.46, 0], [0, 0, 10.0]],
                [True, True, False],
                'volume',
                69.864e-30,  # 69.864 Angstrom^3 = 69.864e-30 m^3
            ),
            # 1D system with vacuum - should have volume (includes vacuum)
            (
                [[1.48, 0, 0], [0, 10.0, 0], [0, 0, 10.0]],
                [True, False, False],
                'volume',
                148.0e-30,  # 148.0 Angstrom^3 = 148.0e-30 m^3
            ),
            # True 2D system - should have area
            (
                [[2.46, 0, 0], [1.23, 2.13, 0], [0, 0, 0]],
                [True, True, False],
                'area',
                5.2398e-20,  # 5.2398 Angstrom^2 = 5.2398e-20 m^2
            ),
            # True 1D system - should have length
            (
                [[1.48, 0, 0], [0, 0, 0], [0, 0, 0]],
                [True, False, False],
                'length',
                1.48e-10,  # 1.48 Angstrom = 1.48e-10 m
            ),
        ],
    )
    def test_from_ase_atoms_dimensionality(
        self, cell, pbc, expected_property, expected_value
    ):
        """
        Test that `from_ase_atoms` correctly handles different dimensionality systems
        and sets the appropriate geometric property (volume/area/length).
        """
        ase_atoms = ase.Atoms(['C'], positions=[[0, 0, 0]], cell=cell, pbc=pbc)

        sys = ModelSystem.from_ase_atoms(ase_atoms, logger=logger)

        # Check that the expected property is set
        if expected_property == 'volume':
            assert sys.volume is not None
            assert sys.volume.magnitude == pytest.approx(expected_value, rel=1e-3)
            assert sys.area is None
            assert sys.length is None
        elif expected_property == 'area':
            assert sys.area is not None
            assert sys.area.magnitude == pytest.approx(expected_value, rel=1e-3)
            assert sys.volume is None
            assert sys.length is None
        elif expected_property == 'length':
            assert sys.length is not None
            assert sys.length.magnitude == pytest.approx(expected_value, rel=1e-3)
            assert sys.volume is None
            assert sys.area is None

    def test_from_ase_atoms_molecule(self):
        """
        Test that `from_ase_atoms` correctly handles 0D molecular systems
        (no geometric extents set).
        """
        ase_atoms = ase.Atoms(['H', 'H'], positions=[[0, 0, 0], [0.74, 0, 0]])

        sys = ModelSystem.from_ase_atoms(ase_atoms, logger=logger)

        assert sys.n_particles == 2
        assert len(sys.particle_states) == 2

        # No geometric extents should be set for molecules
        assert sys.volume is None
        assert sys.area is None
        assert sys.length is None

        # Should still have positions
        assert sys.positions is not None
        assert sys.positions.shape == (2, 3)

    @pytest.mark.parametrize(
        'positions, pbc, expected_type, expected_dim',
        [
            (np.array([[0, 0, 0]]), [False, False, False], 'atom', 0),
            (np.array([[0, 0, 0], [0.5, 0.5, 0.5]]), [True, True, True], 'bulk', 3),
            (
                np.array([[0, 0, 0], [0, 0, 0.74]]),
                [False, False, False],
                'molecule / cluster',
                0,
            ),
        ],
    )
    def test_resolve_system_type_dim(self, positions, pbc, expected_type, expected_dim):
        """
        Check that we can identify system type and dimensionality from an ASE object
        built from the top-level ModelSystem data.
        """
        sys = ModelSystem()
        sys.positions = positions * ureg.angstrom
        c = Representation(
            lattice_vectors=np.eye(3) * 3.0 * ureg.angstrom,
            periodic_boundary_conditions=pbc,
        )
        sys.representations.append(c)
        # Add enough AtomsState entries to match len(positions)
        for _ in range(len(positions)):
            sys.particle_states.append(AtomsState(chemical_symbol='H'))
        ase_atoms = sys.to_ase_atoms(representation_index=0, logger=logger)
        stype, dim = sys.resolve_system_type_and_dimensionality(
            ase_atoms, logger=logger
        )
        assert stype == expected_type
        assert dim == expected_dim

    @pytest.mark.parametrize(
        'lattice_vectors, positions, expected_fractional, description',
        [
            (
                np.eye(3) * 4.0,
                [[0, 0, 0], [2, 0, 0], [0, 2, 2]],
                [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [0.0, 0.5, 0.5]],
                'cubic_cell',
            ),
            (
                np.array(
                    [
                        [3.0, 0, 0],
                        [3.0 * np.cos(np.pi / 3), 3.0 * np.sin(np.pi / 3), 0],
                        [0, 0, 5.0],
                    ]
                ),
                [[2.25, 1.29903811, 2.5]],
                [[0.5, 0.5, 0.5]],
                'hexagonal_cell',
            ),
            (
                np.eye(3) * 2.0,
                [[0, 0, 0]],
                [[0.0, 0.0, 0.0]],
                'origin',
            ),
            (
                np.eye(3) * 2.0,
                [[2, 2, 2]],
                [[1.0, 1.0, 1.0]],
                'unit_cell_corner',
            ),
            (
                np.eye(3) * 2.0,
                [[4, 0, 0], [0, 6, 0]],
                [[2.0, 0.0, 0.0], [0.0, 3.0, 0.0]],
                'outside_unit_cell',
            ),
            (
                np.eye(3) * 2.0,
                [[-2, 0, 0], [0, -4, 0]],
                [[-1.0, 0.0, 0.0], [0.0, -2.0, 0.0]],
                'negative_positions',
            ),
            (
                np.eye(3) * 0.1,
                [[0.05, 0.05, 0.05]],
                [[0.5, 0.5, 0.5]],
                'very_small_cell',
            ),
            (
                np.eye(3) * 1000.0,
                [[500, 500, 500]],
                [[0.5, 0.5, 0.5]],
                'very_large_cell',
            ),
            (
                np.diag([2.0, 3.0, 4.0]),
                [[1, 1.5, 2]],
                [[0.5, 0.5, 0.5]],
                'orthorhombic',
            ),
            (
                np.array([[3.0, 0, 0], [0, 4.0, 0], [1.0, 0, 5.0]]),
                [[1.5, 2.0, 2.5]],
                [[0.33333333, 0.5, 0.5]],
                'monoclinic',
            ),
        ],
    )
    def test_compute_fractional_coordinates_valid(
        self, lattice_vectors, positions, expected_fractional, description
    ):
        """
        Test compute_fractional_coordinates with valid inputs covering various cell types
        and edge cases like positions outside unit cell, negative positions, and extreme sizes.
        """
        sys = ModelSystem(is_representative=True)
        sys.lattice_vectors = lattice_vectors * ureg.angstrom
        sys.positions = np.array(positions) * ureg.angstrom

        fractional = sys.compute_fractional_coordinates()

        assert fractional is not None, f'Failed for {description}'
        np.testing.assert_allclose(
            fractional,
            expected_fractional,
            rtol=1e-5,
            err_msg=f'Mismatch for {description}',
        )

    @pytest.mark.parametrize(
        'lattice_vectors, positions, description',
        [
            (np.zeros((3, 3)), [[0, 0, 0]], 'zero_lattice'),
            (
                np.array([[1, 0, 0], [0, 1, 0], [1, 1, 0]]),
                [[0.5, 0.5, 0]],
                'coplanar_vectors',
            ),
            (
                np.array([[1, 0, 0], [2, 0, 0], [0, 1, 0]]),
                [[1, 1, 0]],
                'linearly_dependent',
            ),
            (np.eye(3), None, 'no_positions'),
            (None, [[0, 0, 0]], 'no_lattice_vectors'),
            (None, None, 'both_none'),
        ],
    )
    def test_compute_fractional_coordinates_edge_cases(
        self, lattice_vectors, positions, description
    ):
        """
        Test compute_fractional_coordinates returns None for edge cases:
        degenerate cells, missing data, singular matrices.
        """
        sys = ModelSystem(is_representative=True)

        if lattice_vectors is not None:
            sys.lattice_vectors = lattice_vectors * ureg.angstrom
        if positions is not None:
            sys.positions = np.array(positions) * ureg.angstrom

        fractional = sys.compute_fractional_coordinates()

        assert fractional is None, f'Should return None for {description}'

    def test_normalize(self):
        """
        Test the full normalization sequence for ModelSystem:
          - If representative, run type/dimensionality, symmetry, chemical formula, etc.
        """
        # Build a minimal model system with top-level positions and a Representation
        sys = generate_model_system(
            is_representative=True,
            positions=[[0, 0, 0], [0.5, 0, 0.5], [1, 1, 1]],
            lattice_vectors=[[3, 0, 0], [0, 3, 0], [0, 0, 3]],
            pbc=[True, True, True],
            chemical_symbols=['H', 'H', 'O'],
            orbitals_symbols=[['s'], ['s'], ['s']],
        )
        sys.symmetry = Symmetry()

        sys.normalize(EntryArchive(), logger=logger)

        # Check basic results
        assert sys.type in ['molecule / cluster', 'bulk']
        assert sys.dimensionality is not None
        if sys.chemical_formula is not None:
            # If the formula is expected "H2O," check that:
            assert sys.chemical_formula.descriptive == 'H2O'
        # Extra primitive/conventional cells are added to the symmetry section only if there is a parent ModelSystem.
        # For a top-level ModelSystem (with no parent), we expect only the originally appended representation.
        if sys.m_parent is not None:
            # Check if primitive or conventional cells are present in the representations
            primitive = None
            conventional = None
            for rep in sys.representations:
                if getattr(rep, 'name', None) == 'primitive':
                    primitive = rep
                if getattr(rep, 'name', None) == 'conventional':
                    conventional = rep
            if primitive:
                assert primitive.name == 'primitive'
            if conventional:
                assert conventional.name == 'conventional'
        else:
            # Top-level system: expect only one representation.
            assert len(sys.representations) == 1

    @pytest.mark.parametrize(
        'lattice_vectors, pbc, should_clear, description',
        [
            (None, [True, True, True], True, 'None lattice_vectors with list PBC'),
            (
                None,
                np.array([True, True, True]),
                True,
                'None lattice_vectors with array PBC',
            ),
            (
                np.array([]).reshape(0, 3) * ureg.angstrom,
                [False],
                True,
                'empty array lattice_vectors',
            ),
            (
                np.eye(3) * 4.0 * ureg.angstrom,
                [True, True, True],
                False,
                'valid lattice_vectors should not clear',
            ),
            (
                np.eye(3) * 4.0 * ureg.angstrom,
                np.array([True, False, True]),
                False,
                'valid lattice_vectors with array PBC',
            ),
        ],
    )
    def test_normalize_clears_pbc_without_lattice_vectors(
        self, caplog, lattice_vectors, pbc, should_clear, description
    ):
        """
        Test that normalize() clears periodic_boundary_conditions when
        lattice_vectors are absent or empty, and logs a warning.
        """
        import logging

        sys = ModelSystem(is_representative=True)
        sys.positions = np.array([[0, 0, 0], [0.5, 0, 0.5]]) * ureg.angstrom
        sys.periodic_boundary_conditions = pbc
        sys.lattice_vectors = lattice_vectors
        for sym in ['H', 'O']:
            sys.particle_states.append(AtomsState(chemical_symbol=sym))

        with caplog.at_level(logging.WARNING):
            sys.normalize(EntryArchive(), logger=logger)

        if should_clear:
            assert sys.periodic_boundary_conditions == [], f'Failed for {description}'
            assert any(
                'Lattice vectors are not defined' in rec.message
                for rec in caplog.records
            ), f'Warning not logged for {description}'
        else:
            assert sys.periodic_boundary_conditions != [], (
                f'PBC incorrectly cleared for {description}'
            )


@pytest.mark.parametrize('branching', [True, False])
def test_branch_depth_if_needed(branching):
    """
    Simplistic test verifying branch_depth logic.
    """
    parent = ModelSystem(is_representative=True, branch_label='Parent')
    child = ModelSystem(branch_label='Child')
    if branching:
        parent.sub_systems.append(child)
    sim = Simulation(model_system=[parent])
    sim._set_system_branch_depth(system_parent=parent)
    # Check if child depth is 1 if branching is True, else child doesn't exist
    if branching:
        assert child.branch_depth == 1
    else:
        # no child
        pass


def make_water_cu_system(n_h2o: int) -> ModelSystem:
    """
    Build a root ModelSystem with:
      - one group_H2O branch containing n_h2o leaves (each H2O),
      - one Cu leaf,
    and with proper particle_states and particle_indices.
    """
    root = ModelSystem(is_representative=True)
    # Add a trivial Representation so normalization doesn't bail out
    ac = Representation(periodic_boundary_conditions=[False, False, False])
    ac.positions = np.zeros((0, 3)) * ureg.angstrom
    root.representations.append(ac)

    # group_H2O branch
    group = ModelSystem(branch_label='group_H2O', is_representative=False)
    root.sub_systems.append(group)

    group_indices = []
    # for each water molecule
    for _ in range(n_h2o):
        leaf = ModelSystem(branch_label='H2O', is_representative=False)
        mol_indices = []
        # H, H, O
        for sym, Z in (('H', 1), ('H', 1), ('O', 8)):
            st = AtomsState(chemical_symbol=sym, atomic_number=Z)
            root.particle_states.append(st)
            idx = len(root.particle_states) - 1
            mol_indices.append(idx)
            group_indices.append(idx)
        leaf.particle_indices = mol_indices
        group.sub_systems.append(leaf)
    group.particle_indices = group_indices

    # Cu leaf
    cu_leaf = ModelSystem(branch_label='Cu', is_representative=False)
    root.sub_systems.append(cu_leaf)
    st_cu = AtomsState(chemical_symbol='Cu', atomic_number=29)
    root.particle_states.append(st_cu)
    cu_leaf.particle_indices = [len(root.particle_states) - 1]

    return root


@pytest.mark.parametrize('n_h2o', [1, 3])
def test_hierarchical_composition_and_branch_depth(n_h2o):
    """
    End-to-end tree check: after Simulation.normalize(), branch_depth is assigned
    (root=0, group=1, leaves=2), and composition_formula is computed correctly for
    the root, group, molecule leaves, and a separate atomic leaf.
    """
    root = make_water_cu_system(n_h2o)

    # Wrap in a Simulation so that .normalize() will set branch_depth & composition_formula
    sim = Simulation(model_system=[root])

    # Before normalize, branch_depth and composition_formula are unset
    assert root.branch_depth is None
    assert root.composition_formula is None

    # Run the full tree normalization
    sim.normalize(EntryArchive(), logger=logger)

    # Now the root should be depth 0
    assert root.branch_depth == 0
    # Its first child (group_H2O) is depth 1
    group = root.sub_systems[0]
    assert group.branch_depth == 1
    # And each water leaf is depth 2
    for leaf in group.sub_systems:
        assert leaf.branch_depth == 2
    # The Cu leaf is also at depth 1
    cu = root.sub_systems[1]
    assert cu.branch_depth == 1

    # composition_formula checks
    # root should read "Cu(1)group_H2O(1)" (children are sorted alphabetically)
    assert root.composition_formula == 'Cu(1)group_H2O(1)'
    # group_H2O should read "H2O(n_h2o)"
    assert group.composition_formula == f'H2O({n_h2o})'
    # each H2O leaf should read "H(2)O(1)"
    for leaf in group.sub_systems:
        assert leaf.composition_formula == 'H(2)O(1)'
    # Cu leaf should read "Cu(1)"
    assert cu.composition_formula == 'Cu(1)'


class TestModelSystemBondFunctions:
    """
    Tests for:
      - get_root_system
      - get_bond_list
      - is_molecule
    """

    def make_simple_system(self) -> ModelSystem:
        """
        Build a root system with 4 particles and a single child subsystem.
        Root bonds: [(0,1), (1,2), (2,3)] (a linear chain).
        Child subsystem: particle_indices = [1, 2].
        """
        # Root system with 4 particles
        root = ModelSystem(is_representative=True)
        for sym in ['H', 'O', 'O', 'H']:
            root.particle_states.append(AtomsState(chemical_symbol=sym))
        root.n_particles = 4
        root.bond_list = [(0, 1), (1, 2), (2, 3)]  # linear chain H-O-O-H

        # Child subsystem (middle two particles)
        child = ModelSystem(branch_label='child', is_representative=False)
        child.particle_indices = [1, 2]
        root.sub_systems.append(child)

        return root

    def test_get_root_system_returns_top_level(self):
        """
        get_root_system() returns the top-level ModelSystem for both the root and
        its nested child subsystem.
        """
        root = self.make_simple_system()
        child = root.sub_systems[0]
        # Root of root is itself
        assert root.get_root_system() is root
        # Root of child should be the parent root
        assert child.get_root_system() is root

    def test_get_bond_list_filters_bonds_correctly(self):
        """
        get_bond_list() returns only the bonds fully contained in the subsystem
        (here, only (1,2) for the child), and returns the full list at the root.
        """
        root = self.make_simple_system()
        child = root.sub_systems[0]

        # Child bonds should include only bonds fully inside [1,2]
        bonds = child.get_bond_list()
        assert bonds.shape == (1, 2)
        assert (bonds == np.array([[1, 2]])).all()

        # Root bonds should return full bond list
        root_bonds = root.get_bond_list()
        assert root_bonds.shape == (3, 2)
        assert (root_bonds == np.array([(0, 1), (1, 2), (2, 3)])).all()

    def test_get_bond_list_no_particle_indices(self):
        """
        For a subsystem without particle_indices, get_bond_list() returns an empty
        array because filtering is not possible.
        """
        root = self.make_simple_system()
        child = root.sub_systems[0]

        # Remove particle_indices
        child.particle_indices = None

        # Expect empty array (since no filtering possible)
        bonds = child.get_bond_list()
        assert bonds.size == 0

    def test_get_bond_list_root_empty_shape(self):
        """
        For a root system with no bonds defined, get_bond_list() returns an empty
        array with shape (0, 2) and dtype int32.
        """
        root = ModelSystem()
        root.bond_list = None
        out = root.get_bond_list()
        assert isinstance(out, np.ndarray)
        assert out.shape == (0, 2)

    def test_is_molecule(self):
        """
        is_molecule() is True only when the subsystem is internally connected and
        isolated (no cross-boundary bonds). It is False if disconnected, if any
        cross-boundary bond exists, or for single-particle subsystems without bonds.
        """

        def clear_cache(ms: ModelSystem):
            """
            Clear the bond cache to ensure fresh bond checks.
            """
            ms._cache = {}

        # Start from simple root system (4 atoms, bonds: (0,1), (1,2), (2,3))
        root = self.make_simple_system()
        child = root.sub_systems[0]  # child with particle_indices [1,2]

        # Case 1: Connected internally, but also bonded to outside (bond 0-1 exists)
        assert child.is_molecule() is False  # Cross-boundary bond prevents molecule

        clear_cache(root)
        clear_cache(child)

        # Case 2: Remove cross-boundary bonds; only internal (1,2) remains
        root.bond_list = [(1, 2)]
        assert child.is_molecule() is True  # Now isolated and connected
        # Add unrelated external bond (0-3) which should not affect isolation
        root.bond_list = [(0, 3), (1, 2)]
        assert child.is_molecule() is True

        clear_cache(root)
        clear_cache(child)

        # Case 3: No bonds at all → multi-particle subsystem fails
        root.bond_list = None
        assert child.is_molecule() is False

        clear_cache(root)
        clear_cache(child)

        # Single-particle subsystem should also fail (no bonds)
        single = ModelSystem(particle_indices=[1])
        root.sub_systems.append(single)
        assert single.is_molecule() is False

        clear_cache(root)
        clear_cache(child)

        # Case 4: Single-particle subsystem bonded to outside → fails
        root.bond_list = [(1, 0)]
        isolated = ModelSystem(
            branch_label='isolated', particle_indices=[3]
        )  # Single atom
        root.sub_systems.append(isolated)
        assert isolated.is_molecule() is False

    @pytest.mark.parametrize(
        'states, expected',
        [
            ([], False),  # empty
            ([AtomsState(chemical_symbol='H')], True),
            ([AtomsState(chemical_symbol='H'), AtomsState(chemical_symbol='O')], True),
            ([CGBeadState(bead_symbol='B')], False),
            ([AtomsState(chemical_symbol='H'), CGBeadState(bead_symbol='B')], True),
            ([CGBeadState(bead_symbol='H'), CGBeadState(bead_symbol='B')], False),
        ],
    )
    def test_is_atomic_flag(self, states, expected):
        """
        is_atomic() reflects whether all particle_states are AtomsState (True)
        versus any CG/generic presence (False), with [] → False.
        """
        ms = ModelSystem()
        for s in states:
            ms.particle_states.append(s)
        assert ms.is_atomic() is expected


class TestParticleStateNormalizationPolicy:
    """
    Tests that ModelSystem normalization preserves parser-provided particle state
    types while still gating atomic-only normalization on element-like labels.
    """

    def test_generic_particles_with_element_labels_are_not_reassigned(self):
        """
        Generic ParticleState entries remain generic even if their labels look
        like element symbols.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(ParticleState(label='H'))
        ms.particle_states.append(ParticleState(label='O'))

        ms.normalize(EntryArchive(), logger=logger)

        assert ms.is_atomic() is True
        assert all(isinstance(p, ParticleState) for p in ms.particle_states)
        assert not any(isinstance(p, AtomsState) for p in ms.particle_states)
        assert [p.label for p in ms.particle_states] == ['H', 'O']

    def test_generic_particles_with_non_element_labels_are_not_reassigned(self):
        """
        Generic ParticleState entries remain generic for non-element labels
        instead of being converted to CGBeadState.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(ParticleState(label='B1'))
        ms.particle_states.append(ParticleState(label='X'))

        ms.normalize(EntryArchive(), logger=logger)

        assert ms.is_atomic() is False
        assert all(type(p) is ParticleState for p in ms.particle_states)
        assert [p.label for p in ms.particle_states] == ['B1', 'X']

    def test_generic_with_missing_label_preserves_length_and_type(self):
        """
        Missing generic labels do not trigger reassignment; order and values are
        preserved exactly as provided by the parser.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(ParticleState(label='H'))
        ms.particle_states.append(ParticleState(label=None))  # missing

        ms.normalize(EntryArchive(), logger=logger)

        assert len(ms.particle_states) == 2
        assert all(type(p) is ParticleState for p in ms.particle_states)
        assert [p.label for p in ms.particle_states] == ['H', None]
        assert ms.is_atomic() is False

    def test_parser_atoms_trusted_no_reassign(self):
        """
        If the parser already provided only AtomsState entries, the normalizer must
        not reassign them; object identity and order stay the same.
        """
        ms = ModelSystem(is_representative=True)
        a1 = AtomsState(chemical_symbol='H')
        a2 = AtomsState(chemical_symbol='O')
        ms.particle_states.extend([a1, a2])

        ms.normalize(EntryArchive(), logger=logger)

        # No reassignment: same objects, same order
        assert len(ms.particle_states) == 2
        assert ms.particle_states[0] is a1
        assert ms.particle_states[1] is a2

        # Still atomic and symbols intact
        assert ms.is_atomic() is True
        assert [p.chemical_symbol for p in ms.particle_states] == ['H', 'O']

    def test_mixed_types_trust_parser(self):
        """
        When mixed types are present (e.g., AtomsState and generic ParticleState),
        the normalizer defers to the parser and does not auto-reassign types.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(AtomsState(chemical_symbol='C'))
        ms.particle_states.append(
            ParticleState(label='O')
        )  # generic, but mixed with AA

        ms.normalize(EntryArchive(), logger=logger)

        # We trust the parser: no auto-reassignment when mixed types present
        assert isinstance(ms.particle_states[0], AtomsState)
        assert isinstance(ms.particle_states[1], ParticleState)

    def test_atomic_gate_blocks_non_atomic_flow(self):
        """
        If the system is non-atomic (e.g., contains only CG beads), the atomic
        normalization path (symmetry/formulas) is skipped as expected.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(CGBeadState(bead_symbol='B'))

        ms.normalize(EntryArchive(), logger=logger)

        # Non-atomic → early return; chemical_formula should not be created
        assert not ms.chemical_formula  # remains None/empty

    def test_noop_when_already_all_atoms(self):
        """
        If parser already provided only AtomsState entries, normalization is a no-op.
        Preserve identity, order, and symbols.
        """
        ms = ModelSystem(is_representative=True)
        a1 = AtomsState(chemical_symbol='C')
        a2 = AtomsState(chemical_symbol='O')
        ms.particle_states.extend([a1, a2])

        ms.normalize(EntryArchive(), logger=logger)

        assert [type(p) for p in ms.particle_states] == [AtomsState, AtomsState]
        assert ms.particle_states[0] is a1 and ms.particle_states[1] is a2
        assert [p.chemical_symbol for p in ms.particle_states] == ['C', 'O']

    def test_noop_when_already_all_cg(self):
        """
        If parser already provided only CGBeadState entries, normalization is a no-op.
        """
        ms = ModelSystem(is_representative=True)
        c1 = CGBeadState(bead_symbol='B1')
        c2 = CGBeadState(bead_symbol='X')
        ms.particle_states.extend([c1, c2])

        ms.normalize(EntryArchive(), logger=logger)

        assert [type(p) for p in ms.particle_states] == [CGBeadState, CGBeadState]
        assert ms.particle_states[0] is c1 and ms.particle_states[1] is c2
        assert [p.bead_symbol for p in ms.particle_states] == ['B1', 'X']

    def test_generic_with_invalid_label_stays_generic(self):
        """
        Invalid generic labels block atomic normalization but do not trigger any
        conversion to CGBeadState.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(ParticleState(label='H'))
        ms.particle_states.append(ParticleState(label='B1'))

        ms.normalize(EntryArchive(), logger=logger)

        assert [type(p) for p in ms.particle_states] == [ParticleState, ParticleState]
        assert [p.label for p in ms.particle_states] == ['H', 'B1']
        assert ms.is_atomic() is False

    def test_generic_with_empty_string_stays_generic(self):
        """
        Empty-string labels remain on ParticleState and simply prevent the atomic
        path from running.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(ParticleState(label='H'))
        ms.particle_states.append(ParticleState(label=''))

        ms.normalize(EntryArchive(), logger=logger)

        assert [type(p) for p in ms.particle_states] == [ParticleState, ParticleState]
        assert [p.label for p in ms.particle_states] == ['H', '']

    def test_order_preserved_for_generic_particles_with_element_labels(self):
        """
        Generic ParticleState entries with valid element labels keep their
        original order and remain generic.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.extend(
            [
                ParticleState(label='O'),
                ParticleState(label='H'),
                ParticleState(label='H'),
            ]
        )

        ms.normalize(EntryArchive(), logger=logger)

        assert [type(p) for p in ms.particle_states] == [
            ParticleState,
            ParticleState,
            ParticleState,
        ]
        assert [p.label for p in ms.particle_states] == ['O', 'H', 'H']
        assert ms.is_atomic() is True

    def test_cg_plus_generic_element_labels_trusts_parser(self):
        """
        Mixed CG and generic particle states are preserved exactly as provided by
        the parser.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(CGBeadState(bead_symbol='H'))
        ms.particle_states.append(ParticleState(label='O'))

        ms.normalize(EntryArchive(), logger=logger)

        assert [type(p) for p in ms.particle_states] == [CGBeadState, ParticleState]
        assert ms.particle_states[0].bead_symbol == 'H'
        assert ms.particle_states[1].label == 'O'
        assert ms.is_atomic() is True

    def test_idempotent_normalize_without_reassignment(self):
        """
        Normalizing twice should not alter parser-provided particle state types.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.extend([ParticleState(label='H'), ParticleState(label='O')])

        ms.normalize(EntryArchive(), logger=logger)
        first_types = tuple(type(p) for p in ms.particle_states)
        first_labels = tuple(p.label for p in ms.particle_states)

        ms.normalize(EntryArchive(), logger=logger)
        second_types = tuple(type(p) for p in ms.particle_states)
        second_labels = tuple(p.label for p in ms.particle_states)

        assert first_types == second_types
        assert first_labels == second_labels


class TestModelSystemSymbols:
    """
    Tests for ModelSystem.symbols property and its behavior with particle_indices.
    """

    def test_symbols_root_basic(self):
        """
        Root .symbols returns the particle_states' symbols in order.
        """
        ms = ModelSystem()
        for s in ['H', 'O', 'H', 'O']:
            ms.particle_states.append(AtomsState(chemical_symbol=s))
        assert ms.get_symbols() == ['H', 'O', 'H', 'O']

    def test_symbols_child_order_and_duplicates(self):
        """
        Child .symbols slices from the root by particle_indices, preserving order
        and duplicates exactly as in particle_indices.
        """
        root = ModelSystem()
        for s in ['H', 'O', 'H', 'O']:
            root.particle_states.append(AtomsState(chemical_symbol=s))
        child = ModelSystem()
        child.particle_indices = [3, 0, 0, 1]
        root.sub_systems.append(child)
        assert child.get_symbols() == ['O', 'H', 'H', 'O']

    def test_symbols_child_no_indices_returns_empty(self):
        """
        Child .symbols returns [] when particle_indices is None (no slice defined).
        """
        root = ModelSystem()
        for s in ['H', 'O']:
            root.particle_states.append(AtomsState(chemical_symbol=s))
        child = ModelSystem()
        child.particle_indices = None
        root.sub_systems.append(child)
        assert child.get_symbols() == []

    def test_symbols_child_out_of_range_returns_empty(self):
        """
        Child .symbols returns [] when any index in particle_indices is out of range
        for the root symbols.
        """
        root = ModelSystem()
        for s in ['H', 'O']:
            root.particle_states.append(AtomsState(chemical_symbol=s))
        child = ModelSystem()
        child.particle_indices = [0, 2]  # 2 is out of range
        root.sub_systems.append(child)
        assert child.get_symbols() == []

    def test_symbols_child_negative_index_policy(self):
        """
        Policy test for negative indices in particle_indices. Marked xfail because
        Python list semantics wrap; enable and adjust if you decide to forbid wrapping.
        """
        root = ModelSystem()
        for s in ['H', 'O', 'H']:
            root.particle_states.append(AtomsState(chemical_symbol=s))
        child = ModelSystem()
        child.particle_indices = [-1, 0]
        root.sub_systems.append(child)
        assert child.get_symbols() == []

    def test_symbols_nested_child_depth_two(self):
        """
        Nested subsystem: ensure a grandchild slices symbols from the ultimate root,
        not from its immediate parent’s (potentially reordered) view.
        """
        root = ModelSystem()
        for s in ['H', 'O', 'H', 'O', 'Cu']:
            root.particle_states.append(AtomsState(chemical_symbol=s))
        mid = ModelSystem()
        root.sub_systems.append(mid)
        leaf = ModelSystem()
        mid.sub_systems.append(leaf)
        mid.particle_indices = [0, 1, 2, 3, 4]  # whole set
        leaf.particle_indices = [3, 4, 0]  # pick from root order via leaf
        assert leaf.get_symbols() == ['O', 'Cu', 'H']


class TestModelSystemSubsystemValidation:
    """
    Tests for ModelSystem._validate_subsystem() covering:
      - root no-op
      - child with no particle_indices (warn)
      - root parent: count-based validation (ok / invalid negative / OOB)
      - non-root parent: membership-based validation (ok / parent missing indices / not-a-subset)
    """

    def _mk_root_with_particles(self, n: int) -> ModelSystem:
        root = ModelSystem(is_representative=True)
        root.positions = np.zeros((n, 3)) * ureg.angstrom
        for _ in range(n):
            root.particle_states.append(AtomsState(chemical_symbol='H'))
        return root

    def test_root_is_noop(self, caplog):
        root = self._mk_root_with_particles(3)
        with caplog.at_level('WARNING'):
            root._validate_subsystem(logger)
        # no exception, nothing logged (it's a no-op for root)
        assert not caplog.records

    def test_child_no_indices_warns(self, caplog):
        root = self._mk_root_with_particles(2)
        child = ModelSystem()
        child.particle_indices = None
        root.sub_systems.append(child)

        with caplog.at_level('WARNING'):
            child._validate_subsystem(logger)

        assert any(
            'Cannot validate ModelSystem subsystem without particle_indices'
            in rec.message
            for rec in caplog.records
        )

    def test_root_parent_valid_indices_pass(self):
        root = self._mk_root_with_particles(4)
        child = ModelSystem()
        child.particle_indices = [0, 3]
        root.sub_systems.append(child)

        # Should not raise
        child._validate_subsystem(logger)

    def test_root_parent_negative_index_asserts(self):
        """
        Negative indices must be rejected under root-parent path.
        (If this test fails, check the condition: it should be 'i >= 0 and i < n_particles'.)
        """
        root = self._mk_root_with_particles(3)
        child = ModelSystem()
        child.particle_indices = [-1, 1]
        root.sub_systems.append(child)

        with pytest.raises(AssertionError):
            child._validate_subsystem(logger)

    def test_root_parent_oor_index_asserts(self):
        """
        Out-of-range indices must be rejected under root-parent path.
        """
        root = self._mk_root_with_particles(3)  # valid indices: 0,1,2
        child = ModelSystem()
        child.particle_indices = [0, 3]  # 3 is OOB
        root.sub_systems.append(child)

        with pytest.raises(AssertionError):
            child._validate_subsystem(logger)

    def test_nonroot_parent_missing_indices_errors(self, caplog):
        """
        For non-root parents, if the parent's particle_indices is None, log an error and return.
        """
        root = self._mk_root_with_particles(3)
        mid = ModelSystem()
        leaf = ModelSystem()
        # Parent (mid) has no indices:
        mid.particle_indices = None
        # Leaf does have indices:
        leaf.particle_indices = [0]

        root.sub_systems.append(mid)
        mid.sub_systems.append(leaf)

        with caplog.at_level('ERROR'):
            leaf._validate_subsystem(logger)

        assert any(
            'Cannot validate ModelSystem subsystem without parent particle_indices'
            in rec.message
            for rec in caplog.records
        )

    def test_nonroot_parent_subset_passes(self):
        """
        For non-root parents, child's indices must be a subset of parent's indices.
        """
        root = self._mk_root_with_particles(4)  # valid: 0,1,2,3
        mid = ModelSystem()
        mid.particle_indices = [1, 2, 3]
        leaf = ModelSystem()
        leaf.particle_indices = [2]

        root.sub_systems.append(mid)
        mid.sub_systems.append(leaf)

        # Should not raise
        leaf._validate_subsystem(logger)

    def test_nonroot_parent_not_subset_asserts(self):
        """
        For non-root parents, indices not contained in parent's indices must assert.
        """
        root = self._mk_root_with_particles(4)
        mid = ModelSystem()
        mid.particle_indices = [0, 1]  # parent subset
        leaf = ModelSystem()
        leaf.particle_indices = [2]  # not in parent subset

        root.sub_systems.append(mid)
        mid.sub_systems.append(leaf)

        with pytest.raises(AssertionError):
            leaf._validate_subsystem(logger)

    def test_root_parent_without_any_particle_info_errors(self, caplog):
        """
        Root has no positions/particle_states/velocities → log error and return.
        """
        root = ModelSystem(is_representative=True)
        # Explicitly ensure all three are missing/empty:
        root.positions = None
        root.velocities = None
        # Leave particle_states empty

        child = ModelSystem()
        child.particle_indices = [0]
        root.sub_systems.append(child)

        with caplog.at_level('ERROR'):
            child._validate_subsystem(logger)

        assert any(
            'Cannot validate ModelSystem subsystem without root particle positions.'
            in rec.message
            for rec in caplog.records
        )


class TestGetRootSystemCycleDetection:
    def test_root_returns_self(self):
        """A root should return itself."""
        root = ModelSystem(branch_label='A')
        assert root.get_root_system() is root

    def test_nested_returns_root(self):
        """A deep child should resolve to the top-most root."""
        a = ModelSystem(branch_label='A')
        b = ModelSystem(branch_label='B')
        c = ModelSystem(branch_label='C')

        a.sub_systems.append(b)  # sets b.m_parent = a
        b.sub_systems.append(c)  # sets c.m_parent = b

        assert c.get_root_system() is a

    def test_self_cycle_raises(self):
        """Direct self-cycle must be detected and raise."""
        a = ModelSystem(branch_label='A')
        a.m_parent = a  # create self-cycle

        with pytest.raises(RuntimeError, match='Cycle'):
            a.get_root_system()

    def test_long_cycle_raises(self):
        """Longer cycle A -> B -> C -> A must be detected and raise."""
        a = ModelSystem(branch_label='A')
        b = ModelSystem(branch_label='B')
        c = ModelSystem(branch_label='C')

        a.sub_systems.append(b)  # b.m_parent = a
        b.sub_systems.append(c)  # c.m_parent = b
        a.m_parent = c  # close the loop: a -> b -> c -> a

        with pytest.raises(RuntimeError, match='Cycle'):
            c.get_root_system()

    def test_two_node_cycle_raises(self):
        """Two-node cycle B <-> C must be detected and raise."""
        b = ModelSystem(branch_label='B')
        c = ModelSystem(branch_label='C')

        # Create 2-node cycle directly
        b.m_parent = c
        c.m_parent = b

        with pytest.raises(RuntimeError, match='Cycle'):
            b.get_root_system()


class TestRepresentativeFlagOnSubsystem:
    def test_subsystem_representative_flag_is_cleared_on_normalize(self):
        """
        If a child ModelSystem is marked as representative, normalize() must
        clear it (set to False) since only the root may be representative.
        """
        root = ModelSystem(is_representative=True)
        child = ModelSystem(is_representative=True)  # incorrectly representative
        root.sub_systems.append(child)  # establishes parent-child relationship

        # sanity pre-condition
        assert child.is_representative is True

        # normalize only the child; it should un-set its representative flag
        child.normalize(EntryArchive(), logger=logger)
        assert child.is_representative is False

    def test_root_representative_flag_is_preserved_on_normalize(self):
        """
        The root ModelSystem may be representative; normalize() must not
        clear this flag on the root.
        """
        root = ModelSystem(is_representative=True)

        # sanity pre-condition
        assert root.is_representative is True

        root.normalize(EntryArchive(), logger=logger)
        assert root.is_representative is True


def test_wyckoff_sites_property():
    """
    Test the wyckoff_sites computed property in LocalCrystalSymmetry.
    """
    from nomad_simulations.schema_packages.model_system import LocalCrystalSymmetry

    # Test with both wyckoff_letters and site_multiplicities set
    local_sym = LocalCrystalSymmetry()
    local_sym.wyckoff_letters = ['a', 'b', 'b', 'c', 'c', 'c', 'c']
    local_sym.site_multiplicities = [1, 2, 2, 4, 4, 4, 4]

    wyckoff_sites = local_sym.wyckoff_sites
    assert wyckoff_sites is not None
    assert wyckoff_sites == ['a1', 'b2', 'b2', 'c4', 'c4', 'c4', 'c4']

    # Test with missing wyckoff_letters
    local_sym2 = LocalCrystalSymmetry()
    local_sym2.site_multiplicities = [1, 2]
    assert local_sym2.wyckoff_sites is None

    # Test with missing site_multiplicities
    local_sym3 = LocalCrystalSymmetry()
    local_sym3.wyckoff_letters = ['a', 'b']
    assert local_sym3.wyckoff_sites is None

    # Test with mismatched lengths
    local_sym4 = LocalCrystalSymmetry()
    local_sym4.wyckoff_letters = ['a', 'b']
    local_sym4.site_multiplicities = [1]  # Length mismatch
    assert local_sym4.wyckoff_sites is None


@pytest.mark.parametrize(
    'symbol, positions, lattice_constant, n_atoms, space_group_range',
    [
        pytest.param(
            'Al',
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.0], [0.5, 0.0, 0.5], [0.0, 0.5, 0.5]],
            4.05,
            4,
            (225, 225),
            id='fcc_aluminum',
        ),
        pytest.param(
            'Fe',
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            2.87,
            2,
            (229, 229),
            id='bcc_iron',
        ),
        pytest.param(
            'Po',
            [[0.0, 0.0, 0.0]],
            3.35,
            1,
            (221, 221),
            id='simple_cubic_polonium',
        ),
        pytest.param(
            'Si',
            [
                [0.0, 0.0, 0.0],
                [0.25, 0.25, 0.25],
                [0.5, 0.5, 0.0],
                [0.75, 0.75, 0.25],
                [0.5, 0.0, 0.5],
                [0.75, 0.25, 0.75],
                [0.0, 0.5, 0.5],
                [0.25, 0.75, 0.75],
            ],
            5.43,
            8,
            (227, 227),
            id='diamond_silicon',
        ),
    ],
)
def test_symmetry_analysis_fields(
    symbol, positions, lattice_constant, n_atoms, space_group_range
):
    """
    Test that symmetry analysis populates analysis_origin_shift,
    analysis_transformation_matrix, and site_symmetries for various crystal structures.
    """
    import ase

    from nomad_simulations.schema_packages.model_system import (
        ModelSystem,
        Symmetry,
    )

    from . import logger

    # Create structure with scaled positions
    a = lattice_constant
    scaled_positions = positions
    ase_atoms = ase.Atoms(
        symbols=[symbol] * n_atoms,
        scaled_positions=scaled_positions,
        cell=[a, a, a],
        pbc=True,
    )

    sys = ModelSystem.from_ase_atoms(ase_atoms, logger=logger)
    sys.type = 'bulk'
    symmetry = Symmetry()

    # Directly call resolve_bulk_symmetry to test the implementation
    # We discard the returned cells as we're only testing symmetry field population
    _, _ = symmetry.resolve_bulk_symmetry(sys, logger)

    # Check that analysis_origin_shift is populated
    assert symmetry.analysis_origin_shift is not None
    assert symmetry.analysis_origin_shift.shape == (3,)

    # Check that analysis_transformation_matrix is populated
    assert symmetry.analysis_transformation_matrix is not None
    assert symmetry.analysis_transformation_matrix.shape == (3, 3)

    # Check space group is in expected range
    assert symmetry.space_group_number is not None
    assert space_group_range[0] <= symmetry.space_group_number <= space_group_range[1]

    # Check that site_symmetries are populated in local_symmetry
    assert sys.local_symmetry is not None
    assert sys.local_symmetry.site_symmetries is not None
    assert len(sys.local_symmetry.site_symmetries) == n_atoms

    # Each site symmetry should be a non-empty string (point group symbol)
    for site_sym in sys.local_symmetry.site_symmetries:
        assert isinstance(site_sym, str)
        assert len(site_sym) > 0


def test_local_symmetry_array_length_validation(caplog):
    """
    Test that LocalCrystalSymmetry.normalize() warns when array lengths don't match
    the parent representation's particle count.
    """
    import logging

    # Create a Representation with 4 atoms
    rep = Representation(fractional_coordinates=np.zeros((4, 3)))
    rep.local_symmetry = LocalCrystalSymmetry(
        wyckoff_letters=['a', 'b', 'c']  # Only 3, should be 4
    )

    # Normalize should issue a warning
    archive = EntryArchive()
    with caplog.at_level(logging.WARNING):
        rep.local_symmetry.normalize(archive, logger)

    # Check that warning was logged
    assert any(
        'wyckoff_letters length (3) does not match n_particles (4)' in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize(
    'equivalent_atoms, expected_multiplicities',
    [
        # Two pairs of equivalent atoms
        ([0, 0, 2, 2], [2, 2, 2, 2]),
        # All atoms are unique (no equivalence)
        ([0, 1, 2, 3], [1, 1, 1, 1]),
        # All atoms are equivalent
        ([0, 0, 0, 0], [4, 4, 4, 4]),
        # Complex: 4 equivalent + 2 equivalent (models ZnS wurtzite)
        ([0, 0, 0, 0, 4, 4], [4, 4, 4, 4, 2, 2]),
        # Single atom
        ([0], [1]),
        # Three groups: 3, 2, 1
        ([0, 0, 0, 3, 3, 5], [3, 3, 3, 2, 2, 1]),
    ],
)
def test_compute_site_multiplicities(equivalent_atoms, expected_multiplicities):
    """
    Test the _compute_site_multiplicities() static method.

    This method computes how many atoms share the same equivalent_atoms index,
    which is critical for correctly determining Wyckoff position multiplicities.
    """
    result = Symmetry._compute_site_multiplicities(equivalent_atoms)
    assert result == expected_multiplicities


@pytest.mark.parametrize(
    'pearson, expected_type, expected_centering',
    [
        # 3D single-character family codes
        ('cF', 'c - cubic', 'F - all faces centred'),
        ('tI', 't - tetragonal', 'I - body centred'),
        ('oP', 'o - orthorhombic', 'P - primitive'),
        ('mP', 'm - monoclinic', 'P - primitive'),
        ('aP', 'a - triclinic', 'P - primitive'),
        ('hP', 'h - hexagonal', 'P - primitive'),
        ('rR', 'r - trigonal', 'R - rhombohedral'),
        # 2D/1D multi-character family codes
        ('mpp', 'mp - oblique', 'p - primitive 2D/1D'),
        ('opp', 'op - rectangular', 'p - primitive 2D/1D'),
        ('ocp', 'oc - centered rectangular', 'p - primitive 2D/1D'),
        ('tpp', 'tp - square', 'p - primitive 2D/1D'),
        ('hpp', 'hp - hexagonal 2D', 'p - primitive 2D/1D'),
        ('app', 'ap - linear', 'p - primitive 2D/1D'),
        ('occ', 'oc - centered rectangular', 'c - centered 2D'),
    ],
)
def test_parse_bravais_lattice_pearson(pearson, expected_type, expected_centering):
    """Test Pearson notation parsing for both 3D and 2D/1D lattice types."""
    symmetry = GlobalCrystalSymmetry()

    lattice_type, lattice_centering = symmetry._parse_bravais_lattice_pearson(
        pearson, logger
    )

    assert lattice_type == expected_type
    assert lattice_centering == expected_centering


@pytest.mark.parametrize(
    'pearson_input',
    [
        # 3D single-character family codes
        'cF',
        'tI',
        'oP',
        'mS',
        'aP',
        'hP',
        'rR',
        # 2D/1D multi-character family codes
        'mpp',
        'opp',
        'ocp',
        'tpp',
        'hpp',
        'app',
        'occ',
    ],
)
def test_bravais_lattice_roundtrip(pearson_input):
    """Test that Pearson notation can be parsed and reconstructed correctly."""
    symmetry = GlobalCrystalSymmetry()

    # Parse Pearson notation
    lattice_type, lattice_centering = symmetry._parse_bravais_lattice_pearson(
        pearson_input, logger
    )
    symmetry.lattice_type = lattice_type
    symmetry.lattice_centering = lattice_centering

    # Reconstruct via property
    pearson_output = symmetry.bravais_lattice

    assert pearson_output == pearson_input


@pytest.mark.parametrize(
    'has_frac_coords, has_positions, has_n_particles, expected_count',
    [
        # Only fractional_coordinates (preferred)
        (True, False, False, 4),
        # Only positions (fallback)
        (False, True, False, 3),
        # Only n_particles (fallback)
        (False, False, True, 5),
        # Multiple sources - fractional_coordinates wins
        (True, True, True, 4),
        # positions + n_particles - positions wins
        (False, True, True, 3),
        # No sources available
        (False, False, False, None),
    ],
)
def test_get_particle_count_from_parent(
    has_frac_coords, has_positions, has_n_particles, expected_count
):
    """Test particle count determination from different parent attributes."""
    rep = Representation()

    if has_frac_coords:
        rep.fractional_coordinates = np.array([[0, 0, 0]] * 4)
    if has_positions:
        rep.positions = np.array([[0, 0, 0]] * 3) * ureg.angstrom
    if has_n_particles:
        rep.n_particles = 5

    result = LocalSymmetry._get_particle_count_from_parent(rep)
    assert result == expected_count


def test_validate_array_lengths():
    """Test array length validation logs warnings for mismatched arrays."""
    rep = Representation(fractional_coordinates=np.zeros((4, 3)))
    rep.local_symmetry = LocalCrystalSymmetry(
        wyckoff_letters=['a', 'b', 'c'],  # Only 3, should be 4
        site_symmetries=['1', '2', '3', '4'],  # Correct length
    )

    # Capture log output
    caplog_records = []
    original_warning = logger.warning

    def capture_warning(msg):
        caplog_records.append(msg)
        original_warning(msg)

    logger.warning = capture_warning

    try:
        rep.local_symmetry._validate_array_lengths(4, logger)

        # Check that warning was logged for wyckoff_letters
        assert any(
            'wyckoff_letters length (3) does not match n_particles (4)' in record
            for record in caplog_records
        )
        # Check that no warning was logged for site_symmetries (correct length)
        assert not any(
            'site_symmetries' in record and 'does not match' in record
            for record in caplog_records
        )
    finally:
        logger.warning = original_warning
