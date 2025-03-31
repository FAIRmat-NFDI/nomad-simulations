import ase
import numpy as np
import pytest
from ase import Atoms
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import (
    AtomDefinition,
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
)

from . import logger


def create_cell(lattice_vectors, pbc):
    """Creates a Cell instance with lattice_vectors and periodic boundary conditions."""
    cell = Cell()
    cell.lattice_vectors = np.array(lattice_vectors) * ureg('angstrom')
    cell.periodic_boundary_conditions = pbc
    return cell


#############################################
# Tests for AtomsState (new style)
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
        # Create an AtomDefinition with the given data.
        atom_def = AtomDefinition(
            chemical_symbol=chemical_symbol, atomic_number=atomic_number
        )
        # Create an AtomsState that references the AtomDefinition.
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
# Tests for ModelSystem (new style)
#############################################
class TestModelSystem:
    def test_from_ase_atoms(self):
        """
        Test that from_ase_atoms() correctly populates:
          - ModelSystem.positions (at the top level)
          - ModelSystem.atom_states (each with an AtomDefinition)
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

        # Check that positions are stored at ModelSystem level.
        np.testing.assert_allclose(ms.positions.to('angstrom').magnitude, positions)
        assert ms.n_atoms == len(positions)
        # Check that atom_states is populated correctly.
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
            atom_def = AtomDefinition(chemical_symbol=sym, atomic_number=num)
            state = AtomsState(atom_definition_ref=atom_def)
            ms.atom_states.append(state)
        # Create a Cell with lattice vectors and PBC.
        cell_instance = create_cell(
            [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [True, True, True]
        )
        ms.cell.append(cell_instance)

        ase_atoms_new = ms.to_ase_atoms(logger)
        assert ase_atoms_new is not None
        # Verify positions
        np.testing.assert_allclose(
            ase_atoms_new.get_positions(), ms.positions.to('angstrom').magnitude
        )
        # Verify chemical symbols
        assert ase_atoms_new.get_chemical_symbols() == symbols
        # Verify cell info (lattice vectors and PBC)
        np.testing.assert_allclose(
            ase_atoms_new.get_cell(),
            cell_instance.lattice_vectors.to('angstrom').magnitude,
        )
        # Use np.array_equal for PBC to avoid ambiguity with arrays.
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
        # Also add a cell so that to_ase_atoms() can use its geometry.
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

        # Create child systems.
        child1 = self.create_system('Child1', 'Child1', 1, atom_indices=[0, 2, 4])
        child2 = self.create_system('Child2', 'Child2', 1, atom_indices=[1, 3, 5])
        # Create grandchild for Child1.
        grandchild1 = self.create_system(
            'Grandchild1', 'Grandchild1', 2, atom_indices=[2, 4]
        )

        # Build hierarchy.
        child1.sub_systems.append(grandchild1)
        parent.sub_systems.append(child1)
        parent.sub_systems.append(child2)

        # Collect hierarchy data.
        hierarchy = self.collect_hierarchy(parent)
        expected = [
            ('ParentSystem', None, 0, None),
            ('Child1', 'Child1', 1, [0, 2, 4]),
            ('Grandchild1', 'Grandchild1', 2, [2, 4]),
            ('Child2', 'Child2', 1, [1, 3, 5]),
        ]
        assert hierarchy == expected, f'Expected {expected} but got {hierarchy}'

        # Verify parent's atom data is unchanged.
        np.testing.assert_allclose(
            parent.positions.to('angstrom').magnitude, parent_positions
        )
        assert len(parent.atom_states) == len(parent_symbols)
        for i, state in enumerate(parent.atom_states):
            assert state.atom_definition_ref.chemical_symbol == parent_symbols[i]

        # Optionally, reconstruct ASE Atoms from parent and verify roundtrip.
        ase_recon = parent.to_ase_atoms(logger)
        assert ase_recon is not None
        np.testing.assert_allclose(
            ase_recon.get_positions(), parent.positions.to('angstrom').magnitude
        )
        assert ase_recon.get_chemical_symbols() == parent_symbols
