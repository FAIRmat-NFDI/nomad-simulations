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


def create_dummy_ase_atoms(symbols, positions, cell_arr, pbc):
    """Creates a dummy ASE Atoms object."""
    return Atoms(symbols=symbols, positions=positions, cell=cell_arr, pbc=pbc)


#############################################
# Tests for AtomsState
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
        state = AtomsState(atom_definition_ref=atom_def)
        # Resolve values.
        resolved_number = state.atom_definition_ref.resolve_atomic_number(logger=logger)
        resolved_symbol = state.atom_definition_ref.resolve_chemical_symbol(
            logger=logger
        )
        assert resolved_number == atomic_number
        assert resolved_symbol == chemical_symbol


#############################################
# Tests for ModelSystem functionality
#############################################
class TestModelSystem:
    def test_from_ase_atoms(self):
        """
        Test that from_ase_atoms() correctly populates:
          - positions at the top level,
          - particle_states (each with an AtomDefn).
        """
        symbols = ['H', 'O', 'H']
        positions = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0]])
        cell_arr = np.eye(3)
        ase_atoms = create_dummy_ase_atoms(
            symbols, positions, cell_arr, [True, True, True]
        )

        ms = ModelSystem()
        ms.from_ase_atoms(ase_atoms, logger)

        # Check positions
        np.testing.assert_allclose(ms.positions.to('angstrom').magnitude, positions)
        assert ms.n_atoms == len(positions)
        # Check that particle_states is populated correctly.
        assert len(ms.particle_states) == len(symbols)
        for i, state in enumerate(ms.particle_states):
            assert state.atom_definition_ref is not None
            assert state.atom_definition_ref.chemical_symbol == symbols[i]
            assert (
                state.atom_definition_ref.atomic_number
                == ase_atoms.get_atomic_numbers()[i]
            )

    def test_to_ase_atoms(self):
        """
        Test that to_ase_atoms() builds an ASE Atoms object using:
          - Chemical symbols from particle_states via their AtomDefn,
          - Positions from the top-level positions,
          - Lattice vectors and PBC from the first Cell.
        """
        symbols = ['H', 'O', 'H']
        positions = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0]])
        ms = ModelSystem()
        ms.positions = positions * ureg('angstrom')
        ms.n_atoms = len(positions)
        # Populate particle_states manually.
        for sym, num in zip(symbols, [1, 8, 1]):
            atom_def = AtomDefn(chemical_symbol=sym, atomic_number=num)
            state = AtomsState(atom_definition_ref=atom_def)
            ms.particle_states.append(state)
        # Attach a Cell.
        cell_instance = create_cell(
            [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [True, True, True]
        )
        ms.cell.append(cell_instance)

        ase_atoms_new = ms.to_ase_atoms(logger)
        assert ase_atoms_new is not None
        np.testing.assert_allclose(
            ase_atoms_new.get_positions(), ms.positions.to('angstrom').magnitude
        )
        assert ase_atoms_new.get_chemical_symbols() == symbols
        np.testing.assert_allclose(
            ase_atoms_new.get_cell(),
            cell_instance.lattice_vectors.to('angstrom').magnitude,
        )
        assert np.array_equal(
            np.array(ase_atoms_new.get_pbc()),
            np.array(cell_instance.periodic_boundary_conditions),
        )

    def test_normalize_non_representative(self):
        """
        Test that normalization does not update type/dimensionality if ModelSystem is not representative.
        """
        ms = ModelSystem(is_representative=False)
        ms.normalize(EntryArchive(), logger)
        assert ms.type is None
        assert ms.dimensionality is None

    def test_normalize_empty_cell(self):
        """
        Test that normalization does not update type/dimensionality if no Cell is present.
        """
        ms = ModelSystem(is_representative=True)
        ms.normalize(EntryArchive(), logger)
        assert ms.type is None
        assert ms.dimensionality is None

    def test_from_and_to_ase_atoms_roundtrip(self):
        """
        Test a roundtrip: create an ASE Atoms object, populate ModelSystem using from_ase_atoms(),
        then reconstruct an ASE Atoms object using to_ase_atoms().
        """
        symbols = ['H', 'O', 'H']
        positions = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0]])
        cell_arr = np.eye(3)
        ase_atoms_in = create_dummy_ase_atoms(
            symbols, positions, cell_arr, [True, True, True]
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


#############################################
# Tests for ModelSystem Hierarchy
#############################################
class TestModelSystemHierarchyAdvanced:
    def create_system(self, name, branch_label, branch_depth, atom_indices=None):
        ms = ModelSystem(name=name)
        ms.branch_label = branch_label
        ms.branch_depth = branch_depth
        if atom_indices is not None:
            ms.atom_indices = atom_indices
        return ms

    def collect_hierarchy(self, system):
        ai = system.atom_indices
        if ai is not None and isinstance(ai, np.ndarray):
            ai = ai.tolist()
        result = [(system.name, system.branch_label, system.branch_depth, ai)]
        for child in system.sub_systems:
            result.extend(self.collect_hierarchy(child))
        return result

    def test_deep_hierarchy_with_grandchild(self):
        parent = ModelSystem(name='ParentSystem', is_representative=True)
        parent.branch_depth = 0
        parent_symbols = ['H', 'O', 'H', 'C', 'N', 'Cl']
        parent_positions = np.array(
            [[0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0], [2, 1, 0]]
        )
        ase_parent = create_dummy_ase_atoms(
            parent_symbols, parent_positions, np.eye(3), [True, True, True]
        )
        parent.from_ase_atoms(ase_parent, logger)
        parent.positions = parent_positions * ureg('angstrom')
        parent.n_atoms = len(parent_positions)
        parent.cell.append(
            create_cell([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [True, True, True])
        )

        child1 = self.create_system('Child1', 'Child1', 1, atom_indices=[0, 2, 4])
        child2 = self.create_system('Child2', 'Child2', 1, atom_indices=[1, 3, 5])
        grandchild1 = self.create_system(
            'Grandchild1', 'Grandchild1', 2, atom_indices=[2, 4]
        )
        child1.sub_systems.append(grandchild1)
        parent.sub_systems.extend([child1, child2])

        hierarchy = self.collect_hierarchy(parent)
        expected = [
            ('ParentSystem', None, 0, None),
            ('Child1', 'Child1', 1, [0, 2, 4]),
            ('Grandchild1', 'Grandchild1', 2, [2, 4]),
            ('Child2', 'Child2', 1, [1, 3, 5]),
        ]
        assert hierarchy == expected, f'Expected {expected} but got {hierarchy}'

        np.testing.assert_allclose(
            parent.positions.to('angstrom').magnitude, parent_positions
        )
        # Verify that particle_states (which now hold chemical info) are unchanged.
        assert len(parent.particle_states) == len(parent_symbols)
        for i, state in enumerate(parent.particle_states):
            assert state.atom_definition_ref.chemical_symbol == parent_symbols[i]

        ase_recon = parent.to_ase_atoms(logger)
        assert ase_recon is not None
        np.testing.assert_allclose(
            ase_recon.get_positions(), parent.positions.to('angstrom').magnitude
        )
        assert ase_recon.get_chemical_symbols() == parent_symbols


#############################################
# Tests for ModelSystem Updates
#############################################
class TestModelSystemUpdates:
    def test_renormalization_update_behavior(self):
        ms = ModelSystem(is_representative=True)
        positions_initial = np.array([[0, 0, 0], [0, 0, 1]])
        ms.positions = positions_initial * ureg('angstrom')
        ms.n_atoms = len(positions_initial)
        cell_mol = create_cell([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [False, False, False])
        ms.cell.append(cell_mol)
        ms.normalize(EntryArchive(), logger)
        initial_type = ms.type
        initial_dim = ms.dimensionality

        positions_bulk = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        ms.positions = positions_bulk * ureg('angstrom')
        ms.n_atoms = len(positions_bulk)
        ms.cell[0] = create_cell([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [True, True, True])
        ms.normalize(EntryArchive(), logger)
        if initial_type is not None or initial_dim is not None:
            assert (ms.type is not None and ms.type != initial_type) or (
                ms.dimensionality is not None and ms.dimensionality != initial_dim
            )
        else:
            assert ms.type is None and ms.dimensionality is None

    def test_symmetry_and_chemical_formula_integration(self):
        class DummyAtomicCell(AtomicCell):
            def to_ase_atoms(self, logger):
                dummy_symbols = ['H', 'H', 'O']
                dummy_positions = np.zeros((3, 3))
                return Atoms(
                    symbols=dummy_symbols,
                    positions=dummy_positions,
                    cell=self.lattice_vectors.to('angstrom').magnitude,
                    pbc=self.periodic_boundary_conditions,
                )

        dummy_cell = DummyAtomicCell()
        dummy_cell.lattice_vectors = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]) * ureg(
            'angstrom'
        )
        dummy_cell.periodic_boundary_conditions = [True, True, True]
        ms = ModelSystem(is_representative=True)
        ms.cell.append(dummy_cell)
        symbols = ['H', 'H', 'O']
        positions = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0]])
        ms.positions = positions * ureg('angstrom')
        ms.n_atoms = len(positions)
        for sym, num in zip(symbols, [1, 1, 8]):
            atom_def = AtomDefn(chemical_symbol=sym, atomic_number=num)
            state = AtomsState(atom_definition_ref=atom_def)
            ms.particle_states.append(state)
        cf = ChemicalFormula()
        ms.chemical_formula = cf
        cf.normalize(EntryArchive(), logger)
        if cf.m_cache:
            comp = cf.m_cache.get('elemental_composition', [])
            assert len(comp) > 0
        symm = Symmetry()
        ms.symmetry.append(symm)
        symm.normalize(EntryArchive(), logger)
        if symm.bravais_lattice is not None:
            assert isinstance(symm.bravais_lattice, str)
            assert len(symm.bravais_lattice) > 0

    def test_reparenting_hierarchy_updates(self):
        ms_parent = ModelSystem(name='ParentSystem')
        symbols = ['H', 'O', 'H', 'C']
        positions = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 0], [1, 1, 0]])
        ase_parent = create_dummy_ase_atoms(
            symbols, positions, np.eye(3), [True, True, True]
        )
        ms_parent.from_ase_atoms(ase_parent, logger)
        ms_parent.positions = positions * ureg('angstrom')
        ms_parent.n_atoms = len(positions)
        child = ModelSystem(name='Child')
        child.atom_indices = [0, 2]
        ms_parent.sub_systems.append(child)
        assert list(child.atom_indices) == [0, 2]
        child.atom_indices = [1, 3]
        assert list(ms_parent.sub_systems[0].atom_indices) == [1, 3]

    def test_deep_hierarchy_stress(self):
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
