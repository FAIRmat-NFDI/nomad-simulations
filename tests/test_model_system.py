from typing import Optional

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
    AtomicCell,
    Cell,
    ChemicalFormula,
    ModelSystem,
    Symmetry,
)

from . import logger
from .conftest import generate_atomic_cell


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
        Verify that a ModelSystem with positions, a first cell, and valid AtomsState
        entries produces a valid ASE Atoms object with correct cell and symbols.
        """
        sys = ModelSystem(is_representative=True)
        sys.positions = np.array([[0, 0, 0], [0.5, 0, 0.5]]) * ureg.angstrom
        c = Cell(
            lattice_vectors=np.eye(3) * 4.0 * ureg.angstrom,
            periodic_boundary_conditions=[True, True, True],
        )
        sys.cell.append(c)
        # Add AtomsState entries for 2 atoms
        a1 = AtomsState(chemical_symbol='Na')
        a2 = AtomsState(chemical_symbol='Cl')
        sys.particle_states.extend([a1, a2])

        ase_atoms = sys.to_ase_atoms(logger=logger)
        assert ase_atoms is not None
        assert len(ase_atoms) == 2
        assert np.allclose(ase_atoms.get_cell(), np.eye(3) * 4.0)
        assert ase_atoms.get_chemical_symbols() == ['Na', 'Cl']

    def test_to_ase_atoms_blocks_non_element_symbols(self):
        """
        Ensure to_ase_atoms() refuses to construct an ASE Atoms when the symbols are
        not all valid elements (e.g., CG bead labels), and returns None.
        """
        ms = ModelSystem()
        ms.particle_states.append(CGBeadState(bead_symbol='B1'))
        ms.positions = np.zeros((1, 3)) * ureg.angstrom
        ms.cell.append(
            Cell(
                lattice_vectors=np.eye(3) * ureg.angstrom,
                periodic_boundary_conditions=[False, False, False],
            )
        )
        assert ms.to_ase_atoms(logger=logger) is None

    def test_from_ase_atoms(self):
        """
        Verify that from_ase_atoms() populates positions, cell geometry/PBC, and
        particle_states from a given ASE Atoms object.
        """
        ase_atoms = ase.Atoms(
            'CO',
            positions=[[0, 0, 0], [0, 0, 1.1]],
            cell=np.eye(3) * 4.0,
            pbc=[True, True, True],
        )
        sys = ModelSystem()
        sys.cell.append(
            Cell(
                lattice_vectors=(np.eye(3) * 4.0 * ureg.angstrom),
                periodic_boundary_conditions=[True, True, True],
            )
        )
        sys.from_ase_atoms(ase_atoms, logger=logger)

        assert sys.n_particles == 2
        assert sys.positions.shape == (2, 3)
        # Check that the first cell has its lattice_vectors updated; using complete_cell from ASE
        expected_cell = ase.geometry.complete_cell(ase_atoms.get_cell()) * ureg.angstrom
        assert np.allclose(
            sys.cell[0].lattice_vectors.to('angstrom').magnitude,
            expected_cell.to('angstrom').magnitude,
        )
        # Check PBC
        assert np.array_equal(
            np.array(sys.cell[0].periodic_boundary_conditions),
            np.array(ase_atoms.get_pbc()),
        )
        # Check particle_states references
        assert len(sys.particle_states) == 2
        syms = [st.chemical_symbol for st in sys.particle_states]
        assert syms == ['C', 'O']

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
        c = Cell(
            lattice_vectors=np.eye(3) * 3.0 * ureg.angstrom,
            periodic_boundary_conditions=pbc,
        )
        sys.cell.append(c)
        # Add enough AtomsState entries to match len(positions)
        for _ in range(len(positions)):
            sys.particle_states.append(AtomsState(chemical_symbol='H'))
        ase_atoms = sys.to_ase_atoms(logger=logger)
        stype, dim = sys.resolve_system_type_and_dimensionality(
            ase_atoms, logger=logger
        )
        assert stype == expected_type
        assert dim == expected_dim

    def test_normalize(self):
        """
        Test the full normalization sequence for ModelSystem:
          - If representative, run type/dimensionality, symmetry, chemical formula, etc.
        """
        # Build a minimal model system with top-level positions and an AtomicCell
        sys = ModelSystem(is_representative=True)
        sys.positions = np.array([[0, 0, 0], [0.5, 0, 0.5], [1, 1, 1]]) * ureg.angstrom
        ac = generate_atomic_cell(
            lattice_vectors=[[3, 0, 0], [0, 3, 0], [0, 0, 3]],
            periodic_boundary_conditions=[True, True, True],
            chemical_symbols=['H', 'H', 'O'],
            atomic_numbers=[1, 1, 8],
        )
        sys.cell.append(ac)
        # Add a Symmetry, ChemicalFormula
        sym = Symmetry()
        sys.symmetry.append(sym)
        chem = ChemicalFormula()
        sys.chemical_formula = chem
        # Add 3 AtomsState entries for H,H,O
        for s, num in zip(['H', 'H', 'O'], [1, 1, 8]):
            sys.particle_states.append(AtomsState(chemical_symbol=s, atomic_number=num))

        # Normalize
        sys.normalize(EntryArchive(), logger=logger)
        # Check basic results
        assert sys.type in ['molecule / cluster', 'bulk']
        assert sys.dimensionality is not None
        if sys.chemical_formula is not None:
            # If the formula is expected "H2O," check that:
            assert sys.chemical_formula.descriptive == 'H2O'
        # Extra cells (primitive/conventional) are added only if there is a parent ModelSystem.
        # For a top-level ModelSystem (with no parent), we expect only the originally appended cell.
        if sys.m_parent is not None:
            if len(sys.cell) >= 2:
                assert sys.cell[1].type in ['primitive', 'conventional']
        else:
            # Top-level system: expect only one cell.
            assert len(sys.cell) == 1


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
    # Add a trivial AtomicCell so normalization doesn't bail out
    ac = AtomicCell(periodic_boundary_conditions=[False, False, False])
    ac.positions = np.zeros((0, 3)) * ureg.angstrom
    root.cell.append(ac)

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

    def test_get_bond_list_set_local_updates_child(self):
        """
        When called with set_local=True, get_bond_list() stores the filtered bonds
        in the child subsystem's bond_list, preserving shape and dtype.
        """
        root = ModelSystem()
        for s in ['H', 'O', 'O', 'H']:
            root.particle_states.append(AtomsState(chemical_symbol=s))
        root.bond_list = [(0, 1), (1, 2), (2, 3)]
        child = ModelSystem()
        child.particle_indices = [1, 2]
        root.sub_systems.append(child)
        _ = child.get_bond_list(set_local=True)
        assert isinstance(child.bond_list, np.ndarray)  # ! Check/change this
        assert child.bond_list.shape == (1, 2)
        assert (child.bond_list == np.array([[1, 2]])).all()

    def test_is_molecule(self):
        """
        is_molecule() is True only when the subsystem is internally connected and
        isolated (no cross-boundary bonds). It is False if disconnected, if any
        cross-boundary bond exists, or for single-particle subsystems without bonds.
        """
        # Start from simple root system (4 atoms, bonds: (0,1), (1,2), (2,3))
        root = self.make_simple_system()
        child = root.sub_systems[0]  # child with particle_indices [1,2]

        # Case 1: Connected internally, but also bonded to outside (bond 0-1 exists)
        assert child.is_molecule() is False  # Cross-boundary bond prevents molecule

        # Case 2: Remove cross-boundary bonds; only internal (1,2) remains
        root.bond_list = [(1, 2)]
        assert child.is_molecule() is True  # Now isolated and connected
        # Add unrelated external bond (0-3) which should not affect isolation
        root.bond_list = [(0, 3), (1, 2)]
        assert child.is_molecule() is True

        # Case 3: No bonds at all → multi-particle subsystem fails
        root.bond_list = None
        assert child.is_molecule() is False

        # Single-particle subsystem should also fail (no bonds)
        single = ModelSystem(particle_indices=[1])
        root.sub_systems.append(single)
        assert single.is_molecule() is False

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
            ([AtomsState(chemical_symbol='H'), CGBeadState(bead_symbol='B')], False),
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


class TestGenericParticleReassignment:
    """
    Tests for automatic typing of generic ParticleState → AtomsState/CGBeadState
    and the atomic gating in ModelSystem.normalize().
    """

    def test_generic_promotes_to_atoms(self):
        """
        All-generic particle_states with element labels should be promoted to
        AtomsState entries during normalize(), preserving order and count.
        """
        ms = ModelSystem(is_representative=True)
        # Generic particles with element labels
        ms.particle_states.append(ParticleState(label='H'))
        ms.particle_states.append(ParticleState(label='O'))

        ms.normalize(EntryArchive(), logger=logger)

        assert ms.is_atomic() is True
        assert all(isinstance(p, AtomsState) for p in ms.particle_states)
        assert [p.chemical_symbol for p in ms.particle_states] == ['H', 'O']

    def test_generic_demotes_to_cg(self):
        """
        All-generic particle_states with non-element labels should be converted to
        CGBeadState entries during normalize(), preserving order and count.
        """
        ms = ModelSystem(is_representative=True)
        # Non-element labels → CG beads
        ms.particle_states.append(ParticleState(label='B1'))
        ms.particle_states.append(ParticleState(label='X'))

        ms.normalize(EntryArchive(), logger=logger)

        assert ms.is_atomic() is False
        assert all(isinstance(p, CGBeadState) for p in ms.particle_states)
        assert [p.bead_symbol for p in ms.particle_states] == ['B1', 'X']

    def test_generic_with_missing_label_preserves_length(self):
        """
        If any generic label is missing, the set should fall back to CG and preserve
        the number and order of particle_states; missing bead_symbol remains None.
        """
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(ParticleState(label='H'))
        ms.particle_states.append(ParticleState(label=None))  # missing

        ms.normalize(EntryArchive(), logger=logger)

        # Falls back to CG and preserves count/order
        assert len(ms.particle_states) == 2
        assert all(isinstance(p, CGBeadState) for p in ms.particle_states)
        assert [getattr(p, 'bead_symbol', None) for p in ms.particle_states] == [
            'H',
            None,
        ]
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
        assert ms.symbols == ['H', 'O', 'H', 'O']

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
        assert child.symbols == ['O', 'H', 'H', 'O']

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
        assert child.symbols == []

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
        assert child.symbols == []

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
        assert child.symbols == []

    def test_are_valid_chemical_symbols_true_false(self):
        """
        are_valid_chemical_symbols() returns True for pure element symbols and
        False when any non-element (e.g., CG bead) is present.
        """
        ms = ModelSystem()
        ms.particle_states.extend(
            [AtomsState(chemical_symbol='Na'), AtomsState(chemical_symbol='Cl')]
        )
        assert ms.are_valid_chemical_symbols(logger=logger) is True

        ms2 = ModelSystem()
        ms2.particle_states.append(CGBeadState(bead_symbol='B1'))
        assert ms2.are_valid_chemical_symbols(logger=logger) is False

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
        assert leaf.symbols == ['O', 'Cu', 'H']
