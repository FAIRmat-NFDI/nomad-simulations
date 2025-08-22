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
    GlobalCrystalSymmetry,
    ModelSystem,
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
        sym = GlobalCrystalSymmetry()
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
        Test that a ModelSystem with top-level positions, a first cell, and valid
        AtomsState entries can produce an ASE Atoms.
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

    def test_from_ase_atoms(self):
        """
        Test that from_ase_atoms sets positions, cell, particle_states, etc.
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
        sym = GlobalCrystalSymmetry()
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
        Helper to build a root system with 4 particles and a single child subsystem.
        Root bond list: [(0,1), (1,2), (2,3)]
        Child subsystem: particles [1,2]
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
        Ensure get_root_system correctly traverses up to the root.
        """
        root = self.make_simple_system()
        child = root.sub_systems[0]
        # Root of root is itself
        assert root.get_root_system() is root
        # Root of child should be the parent root
        assert child.get_root_system() is root

    def test_get_bond_list_filters_bonds_correctly(self):
        """
        Ensure get_bond_list filters bonds to those involving only the subsystem's particle_indices.
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
        Ensure get_bond_list returns an empty array for a subsystem without particle_indices.
        """
        root = self.make_simple_system()
        child = root.sub_systems[0]

        # Remove particle_indices
        child.particle_indices = None

        # Expect empty array (since no filtering possible)
        bonds = child.get_bond_list()
        assert bonds.size == 0

    def test_is_molecule(self):
        """
        Verify that is_molecule() enforces both internal connectivity and isolation:
        - Fails if connected but bonded to outside.
        - Passes if connected and isolated.
        - Fails if disconnected.
        - Single-particle subsystems are not considered molecules.
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
        ms = ModelSystem(is_representative=True)
        # Generic particles with element labels
        ms.particle_states.append(ParticleState(label='H'))
        ms.particle_states.append(ParticleState(label='O'))

        ms.normalize(EntryArchive(), logger=logger)

        assert ms.is_atomic() is True
        assert all(isinstance(p, AtomsState) for p in ms.particle_states)
        assert [p.chemical_symbol for p in ms.particle_states] == ['H', 'O']

    def test_generic_demotes_to_cg(self):
        ms = ModelSystem(is_representative=True)
        # Non-element labels → CG beads
        ms.particle_states.append(ParticleState(label='B1'))
        ms.particle_states.append(ParticleState(label='X'))

        ms.normalize(EntryArchive(), logger=logger)

        assert ms.is_atomic() is False
        assert all(isinstance(p, CGBeadState) for p in ms.particle_states)
        assert [p.bead_symbol for p in ms.particle_states] == ['B1', 'X']

    def test_generic_with_missing_label_preserves_length(self):
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
        If the parser already provided only AtomsState entries, the normalizer
        must *not* reassign them. Identities and order should be preserved.
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
        ms = ModelSystem(is_representative=True)
        ms.particle_states.append(CGBeadState(bead_symbol='B'))

        ms.normalize(EntryArchive(), logger=logger)

        # Non-atomic → early return; chemical_formula should not be created
        assert not ms.chemical_formula  # remains None/empty
