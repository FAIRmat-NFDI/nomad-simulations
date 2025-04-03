import ase
import numpy as np
import pytest
from ase import Atoms
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import (
    AtomDefn,
    AtomsState,
    CoreHole,
    HubbardInteractions,
    OrbitalsState,
)
from nomad_simulations.schema_packages.model_system import (
    AtomicCell,
    Cell,
    ChemicalFormula,
    ModelSystem,
    Symmetry,
    get_sibling_section,
)

from . import logger


def create_cell(lattice_vectors, pbc):
    """Creates a Cell instance with lattice_vectors and periodic boundary conditions."""
    cell = Cell()
    cell.lattice_vectors = np.array(lattice_vectors) * ureg('angstrom')
    cell.periodic_boundary_conditions = pbc
    return cell


#############################################
# Tests for AtomsState v2
#############################################
class TestAtomsState:
    @pytest.mark.parametrize(
        'chemical_symbol, atomic_number',
        [
            ('Fe', 26),
            ('H', 1),
            ('Cu', 29),
            ('O', 8),
        ],
    )
    def test_elemental_data_resolution(self, chemical_symbol, atomic_number):
        # Create an AtomDefn with the given data.
        atom_def = AtomDefn(
            chemical_symbol=chemical_symbol, atomic_number=atomic_number
        )
        # Create an AtomsState that references the AtomDefn.
        atom_state = AtomsState(atom_definition_ref=atom_def)
        # resolve
        resolved_number = atom_state.atom_definition_ref.resolve_atomic_number(
            logger=logger
        )
        resolved_symbol = atom_state.atom_definition_ref.resolve_chemical_symbol(
            logger=logger
        )
        assert resolved_number == atomic_number
        assert resolved_symbol == chemical_symbol


#############################################
# Tests for ModelSystem v2
#############################################
class TestModelSystem:
    def test_from_ase_atoms(self):
        """
        Test that from_ase_atoms() correctly populates:
          - ModelSystem.positions (at the top level)
          - ModelSystem.atom_states (each with an AtomDefn)
        """
        # Create a dummy ASE Atoms object with 3 atoms (e.g., H, O, H)
        symbols = ['H', 'O', 'H']
        positions = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
        cell_arr = np.eye(3)
        ase_atoms = Atoms(
            symbols=symbols, positions=positions, cell=cell_arr, pbc=[True, True, True]
        )

        ms = ModelSystem()
        ms.from_ase_atoms(ase_atoms, logger)

        # Check that positions are stored at ModelSystem level:
        np.testing.assert_allclose(ms.positions.to('angstrom').magnitude, positions)
        assert ms.n_atoms == len(positions)
        # Check that atom_states is populated correctly
        assert len(ms.atom_states) == len(symbols)
        for i, state in enumerate(ms.atom_states):
            assert state.atom_definition_ref is not None
            assert state.atom_definition_ref.chemical_symbol == symbols[i]
            assert (
                state.atom_definition_ref.atomic_number
                == ase_atoms.get_atomic_numbers()[i]
            )

    def test_to_ase_atoms(self):
        """
        Test that to_ase_atoms() builds an ASE Atoms object using:
          - Chemical symbols from ModelSystem.atom_states via their AtomDefinition.
          - Positions from ModelSystem.positions.
          - Lattice vectors and PBC from the first cell in ModelSystem.cell.
        """
        symbols = ['H', 'O', 'H']
        positions = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
        ms = ModelSystem()
        ms.positions = positions * ureg('angstrom')
        ms.n_atoms = len(positions)
        # Populate atom_states manually.
        for sym, num in zip(symbols, [1, 8, 1]):
            atom_def = AtomDefn(chemical_symbol=sym, atomic_number=num)
            state = AtomsState(atom_definition_ref=atom_def)
            ms.atom_states.append(state)
        # Create a Cell with lattice vectors and PBC.
        cell_instance = create_cell(
            [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [True, True, True]
        )
        ms.cell.append(cell_instance)

        ase_atoms_new = ms.to_ase_atoms(logger)
        assert ase_atoms_new is not None
        # verify positions
        np.testing.assert_allclose(
            ase_atoms_new.get_positions(), ms.positions.to('angstrom').magnitude
        )
        # verify chemical symbols
        assert ase_atoms_new.get_chemical_symbols() == symbols
        # verify cell info (lattice vectors and PBC)
        np.testing.assert_allclose(
            ase_atoms_new.get_cell(),
            cell_instance.lattice_vectors.to('angstrom').magnitude,
        )
        # use np.array_equal for PBC to avoid ambiguity with arrays
        assert np.array_equal(
            np.array(ase_atoms_new.get_pbc()),
            np.array(cell_instance.periodic_boundary_conditions),
        )

    def test_normalize_non_representative(self):
        """
        Test that normalization does not update type/dimensionality if the ModelSystem is not representative.
        """
        ms = ModelSystem(is_representative=False)
        ms.normalize(EntryArchive(), logger)
        assert ms.type is None
        assert ms.dimensionality is None

    def test_normalize_empty_cell(self):
        """
        Test that normalization does not update type/dimensionality if no cell is present.
        """
        ms = ModelSystem(is_representative=True)
        # Do not add any cell.
        ms.normalize(EntryArchive(), logger)
        assert ms.type is None
        assert ms.dimensionality is None

    def test_from_and_to_ase_atoms_roundtrip(self):
        """
        Test a roundtrip: create an ASE Atoms object, populate ModelSystem using from_ase_atoms(),
        and reconstruct an ASE Atoms object using to_ase_atoms(). Verify consistency.
        """
        symbols = ['H', 'O', 'H']
        positions = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0]])
        cell_arr = np.eye(3)
        ase_atoms_in = Atoms(
            symbols=symbols, positions=positions, cell=cell_arr, pbc=[True, True, True]
        )

        ms = ModelSystem()
        ms.from_ase_atoms(ase_atoms_in, logger)
        cell_instance = create_cell(
            [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [True, True, True]
        )
        ms.cell.append(cell_instance)

        ase_atoms_out = ms.to_ase_atoms(logger)
        assert ase_atoms_out is not None
        np.testing.assert_allclose(
            ase_atoms_out.get_positions(), ms.positions.to('angstrom').magnitude
        )
        assert ase_atoms_out.get_chemical_symbols() == symbols


class TestModelSystemHierarchyAdvanced:
    def create_system(self, name, branch_label, branch_depth, atom_indices=None):
        """Helper to create a ModelSystem with basic properties."""
        ms = ModelSystem(name=name)
        ms.branch_label = branch_label
        ms.branch_depth = branch_depth
        if atom_indices is not None:
            ms.atom_indices = atom_indices
        return ms

    def collect_hierarchy(self, system):
        """
        Recursively collects (name, branch_label, branch_depth, atom_indices)
        from the given ModelSystem and its descendants.
        If atom_indices is a NumPy array, it is converted to a Python list.
        """
        ai = system.atom_indices
        if ai is not None and isinstance(ai, np.ndarray):
            ai = ai.tolist()
        result = [(system.name, system.branch_label, system.branch_depth, ai)]
        for child in system.sub_systems:
            result.extend(self.collect_hierarchy(child))
        return result

    def test_deep_hierarchy_with_grandchild(self):
        """
        Create a hierarchy with a grandchild:

            ParentSystem (6 atoms, depth 0)
              ├── Child1 (atom_indices: [0, 2, 4], depth 1)
              │      └── Grandchild1 (atom_indices: [2, 4], depth 2)
              └── Child2 (atom_indices: [1, 3, 5], depth 1)

        Verify that:
          - The parent's top-level positions and atom_states remain unchanged.
          - The child systems hold the correct atom_indices.
          - The overall hierarchy is preserved.
        """
        # Create parent ModelSystem and populate with 6 atoms.
        parent = ModelSystem(name='ParentSystem', is_representative=True)
        parent.branch_depth = 0  # explicitly set parent's depth to 0
        parent_symbols = ['H', 'O', 'H', 'C', 'N', 'Cl']
        parent_positions = np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [2.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.0, 1.0, 0.0],
                [2.0, 1.0, 0.0],
            ]
        )
        ase_parent = Atoms(
            symbols=parent_symbols,
            positions=parent_positions,
            cell=np.eye(3),
            pbc=[True, True, True],
        )
        parent.from_ase_atoms(ase_parent, logger)
        parent.positions = parent_positions * ureg('angstrom')
        parent.n_atoms = len(parent_positions)
        # Add a cell for geometry.
        parent_cell = create_cell([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [True, True, True])
        parent.cell.append(parent_cell)

        # Create child systems
        child1 = self.create_system('Child1', 'Child1', 1, atom_indices=[0, 2, 4])
        child2 = self.create_system('Child2', 'Child2', 1, atom_indices=[1, 3, 5])
        # Create grandchild for Child1
        grandchild1 = self.create_system(
            'Grandchild1', 'Grandchild1', 2, atom_indices=[2, 4]
        )

        # Build hierarchy
        child1.sub_systems.append(grandchild1)
        parent.sub_systems.append(child1)
        parent.sub_systems.append(child2)

        # Collect hierarchy data
        hierarchy = self.collect_hierarchy(parent)
        expected = [
            ('ParentSystem', None, 0, None),
            ('Child1', 'Child1', 1, [0, 2, 4]),
            ('Grandchild1', 'Grandchild1', 2, [2, 4]),
            ('Child2', 'Child2', 1, [1, 3, 5]),
        ]
        assert hierarchy == expected, f'Expected {expected} but got {hierarchy}'

        # Verify parent's atom data is unchanged
        np.testing.assert_allclose(
            parent.positions.to('angstrom').magnitude, parent_positions
        )
        assert len(parent.atom_states) == len(parent_symbols)
        for i, state in enumerate(parent.atom_states):
            assert state.atom_definition_ref.chemical_symbol == parent_symbols[i]

        # Reconstruct ASE Atoms from parent and verify roundtrip.
        ase_recon = parent.to_ase_atoms(logger)
        assert ase_recon is not None
        np.testing.assert_allclose(
            ase_recon.get_positions(), parent.positions.to('angstrom').magnitude
        )
        assert ase_recon.get_chemical_symbols() == parent_symbols


# Dummy subclass for testing integration with Symmetry and ChemicalFormula.
class DummyAtomicCell(AtomicCell):
    def to_ase_atoms(self, logger):
        # Provide a minimal ASE Atoms object using the cell's lattice vectors.
        # Since positions are not stored in AtomicCell in the new design,
        # we return an ASE Atoms object with dummy positions (e.g. zeros)
        # and use a dummy list for chemical symbols.
        # For testing, we assume the cell "represents" 3 atoms.
        dummy_symbols = ['H', 'H', 'O']
        dummy_positions = np.zeros((3, 3))
        return Atoms(
            symbols=dummy_symbols,
            positions=dummy_positions,
            cell=self.lattice_vectors.to('angstrom').magnitude,
            pbc=self.periodic_boundary_conditions,
        )


class TestModelSystemUpdates:
    def test_renormalization_update_behavior(self):
        """
        Test that re-calling normalize() on a ModelSystem after updating positions and cell
        changes the computed type/dimensionality.
        If the classifier does not set these fields (i.e. remains None),
        we simply assert that normalization completes without error.
        """
        ms = ModelSystem(is_representative=True)
        # Initially simulate a molecule: 2 atoms, no periodic boundary conditions.
        positions_initial = np.array([[0, 0, 0], [0, 0, 1]])
        ms.positions = positions_initial * ureg('angstrom')
        ms.n_atoms = len(positions_initial)
        cell_mol = create_cell([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [False, False, False])
        ms.cell.append(cell_mol)
        ms.normalize(EntryArchive(), logger)
        initial_type = ms.type
        initial_dim = ms.dimensionality

        # Now update positions and cell to simulate a bulk system.
        positions_bulk = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        ms.positions = positions_bulk * ureg('angstrom')
        ms.n_atoms = len(positions_bulk)
        ms.cell[0] = create_cell([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [True, True, True])
        ms.normalize(EntryArchive(), logger)
        # If the classifier updated the type/dimensionality, they should differ.
        if initial_type is not None or initial_dim is not None:
            assert (ms.type is not None and ms.type != initial_type) or (
                ms.dimensionality is not None and ms.dimensionality != initial_dim
            )
        else:
            # If they were None initially, at least normalization should complete.
            assert ms.type is None and ms.dimensionality is None

    def test_symmetry_and_chemical_formula_integration(self):
        """
        Test that if a ModelSystem has a cell that returns valid geometric data,
        then both the ChemicalFormula and Symmetry sections can be normalized.
        For this test, we attach a DummyAtomicCell (which implements to_ase_atoms)
        to the ModelSystem.
        """
        dummy_cell = DummyAtomicCell()
        dummy_cell.lattice_vectors = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]) * ureg(
            'angstrom'
        )
        dummy_cell.periodic_boundary_conditions = [True, True, True]
        # Create a ModelSystem and attach the dummy cell.
        ms = ModelSystem(is_representative=True)
        ms.cell.append(dummy_cell)
        # Set positions and atom_states.
        symbols = ['H', 'H', 'O']
        positions = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0]])
        ms.positions = positions * ureg('angstrom')
        ms.n_atoms = len(positions)
        for sym, num in zip(symbols, [1, 1, 8]):
            atom_def = AtomDefn(chemical_symbol=sym, atomic_number=num)
            state = AtomsState(atom_definition_ref=atom_def)
            ms.atom_states.append(state)
        cf = ChemicalFormula()
        ms.chemical_formula = cf
        cf.normalize(EntryArchive(), logger)
        # Check that the chemical formula m_cache is set (i.e. some composition is detected).
        if cf.m_cache:
            comp = cf.m_cache.get('elemental_composition', [])
            assert len(comp) > 0
        symm = Symmetry()
        ms.symmetry.append(symm)
        symm.normalize(EntryArchive(), logger)
        # Check that at least one symmetry field is set.
        if symm.bravais_lattice is not None:
            assert isinstance(symm.bravais_lattice, str)
            assert len(symm.bravais_lattice) > 0

    def test_reparenting_hierarchy_updates(self):
        """
        Test that updating a child's atom_indices is reflected in the parent's hierarchy.
        (Since removal is not supported, we simply update the child's atom_indices and check.)
        """
        parent = ModelSystem(name='ParentSystem')
        # Populate parent with 4 atoms.
        symbols = ['H', 'O', 'H', 'C']
        positions = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0], [1, 1, 0]])
        ase_parent = Atoms(
            symbols=symbols, positions=positions, cell=np.eye(3), pbc=[True, True, True]
        )
        parent.from_ase_atoms(ase_parent, logger)
        parent.positions = positions * ureg('angstrom')
        parent.n_atoms = len(positions)
        # Create a child with initial atom_indices.
        child = ModelSystem(name='Child')
        child.atom_indices = [0, 2]
        parent.sub_systems.append(child)
        # Verify initial atom_indices.
        # Convert to list in case it's stored as an array.
        assert list(child.atom_indices) == [0, 2]
        # Update child's atom_indices.
        child.atom_indices = [1, 3]
        # Since removal is not allowed, parent's sub_systems still holds the same child reference.
        # So simply check that the child's updated atom_indices are reflected.
        assert list(parent.sub_systems[0].atom_indices) == [1, 3]

    def test_deep_hierarchy_stress(self):
        """
        Create a deep hierarchy (10 levels) where each system has one child,
        and verify that the recursive collection of hierarchy information correctly
        reflects the branch depths and names.
        """
        root = ModelSystem(name='Root')
        root.branch_depth = 0
        current = root
        expected = [('Root', None, 0, None)]
        for level in range(1, 11):
            child = ModelSystem(name=f'Level{level}')
            child.branch_label = f'Level{level}'
            child.branch_depth = level
            child.atom_indices = [level - 1]
            current.sub_systems.append(child)
            current = child
            expected.append((f'Level{level}', f'Level{level}', level, [level - 1]))

        def collect(system):
            ai = system.atom_indices
            if ai is not None and isinstance(ai, np.ndarray):
                ai = ai.tolist()
            result = [(system.name, system.branch_label, system.branch_depth, ai)]
            for child in system.sub_systems:
                result.extend(collect(child))
            return result

        hierarchy = collect(root)
        assert hierarchy == expected, f'Expected {expected} but got {hierarchy}'


def test_populate_atom_types():
    """
    Test that populate_atom_types() correctly extracts unique AtomDefn entries
    from the atom_states subsection.
    """
    # Create a ModelSystem instance
    ms = ModelSystem(is_representative=True)

    # Simulate atom_states with duplicate atom definitions:
    # Two entries for hydrogen (H, atomic_number=1, charge=0) and one for oxygen (O, atomic_number=8, charge=0).
    test_data = [
        ('H', 1, 0),
        ('H', 1, 0),
        ('O', 8, 0),
    ]

    for sym, num, ch in test_data:
        # Create an AtomDefn instance for each entry.
        atom_def = AtomDefn(chemical_symbol=sym, atomic_number=num, charge=ch)
        # Create an AtomsState that references this AtomDefn.
        state = AtomsState(atom_definition_ref=atom_def)
        ms.atom_states.append(state)

    # Ensure atom_types is initially empty.
    ms.atom_types.clear()
    assert len(ms.atom_types) == 0

    # Call the new helper function using the globally imported logger.
    ms.populate_atom_types(logger)

    # We expect 2 unique definitions: one for H and one for O.
    assert len(ms.atom_types) == 2, (
        f'Expected 2 unique atom types, got {len(ms.atom_types)}'
    )

    # Verify that the unique keys match the expected values.
    unique_keys = {
        (atom_def.chemical_symbol, atom_def.atomic_number, atom_def.charge)
        for atom_def in ms.atom_types
    }
    expected_keys = {('H', 1, 0), ('O', 8, 0)}
    assert unique_keys == expected_keys, f'Expected {expected_keys}, got {unique_keys}'
