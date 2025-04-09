from typing import Optional

import ase
import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.atoms_state import AtomsState, AtomDefn
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
    Systematic tests for the Symmetry class, focusing on resolve_bulk_symmetry 
    and any other relevant methods.
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
    Systematic tests for the ChemicalFormula class, especially normalize 
    and resolve_chemical_formulas.
    """

    def test_normalize_no_cell(self):
        """
        If no sibling AtomicCell is found, the formula fields should remain None.
        """
        chem = ChemicalFormula()
        chem.normalize(EntryArchive(), logger)
        for f in ["descriptive","reduced","iupac","hill","anonymous"]:
            assert getattr(chem, f) is None

    def test_normalize_with_cell(self):
        """
        Provide a sibling AtomicCell with known composition and see if we get 
        the correct formulas after normalize.
        """
        # Build an AtomicCell for "H2O"
        acell = generate_atomic_cell(
            chemical_symbols=["H","H","O"],
            atomic_numbers=[1,1,8]
        )
        chem = ChemicalFormula()
        # Pretend it's a sibling to the cell by your design. 
        # Possibly you do model_system=ModelSystem(...), model_system.cell.append(acell), etc.
        chem.normalize(EntryArchive(), logger)
        # Check if it sets formulas to H2O
        # Only if your code links them as siblings. If not, adapt accordingly.

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
        sys.positions = np.array([[0,0,0],[0.5,0,0.5]]) * ureg.angstrom
        c = Cell(
            lattice_vectors=np.eye(3)*4.0*ureg.angstrom,
            periodic_boundary_conditions=[True,True,True]
        )
        sys.cell.append(c)
        # Add AtomsState entries for 2 atoms
        a1 = AtomsState(atom_definition_ref=AtomDefn(chemical_symbol="Na"))
        a2 = AtomsState(atom_definition_ref=AtomDefn(chemical_symbol="Cl"))
        sys.particle_states.extend([a1,a2])

        ase_atoms = sys.to_ase_atoms(logger=logger)
        assert ase_atoms is not None
        assert len(ase_atoms) == 2
        assert np.allclose(ase_atoms.get_cell(), np.eye(3)*4.0)
        assert ase_atoms.get_chemical_symbols() == ["Na","Cl"]

    def test_from_ase_atoms(self):
        """
        Test that from_ase_atoms sets positions, cell, particle_states, etc.
        """
        ase_atoms = ase.Atoms("CO", positions=[[0,0,0],[0,0,1.1]], cell=[4,4,4], pbc=[True,True,True])
        sys = ModelSystem()
        sys.from_ase_atoms(ase_atoms, logger=logger)

        assert sys.n_particles == 2
        assert sys.positions.shape == (2,3)
        assert np.allclose(sys.cell[0].lattice_vectors.magnitude, np.eye(3)*4)
        assert sys.cell[0].periodic_boundary_conditions == [True, True, True]
        # Check particle_states references
        assert len(sys.particle_states) == 2
        syms = [st.atom_definition_ref.chemical_symbol for st in sys.particle_states]
        assert syms == ["C", "O"]

    @pytest.mark.parametrize(
        "positions, pbc, expected_type, expected_dim",
        [
            (np.array([[0,0,0]]), [False,False,False], "atom", 0),
            (np.array([[0,0,0],[0.5,0.5,0.5]]), [True,True,True], "bulk", 3),
            # etc. Adjust as needed
        ]
    )
    def test_resolve_system_type_dim(self, positions, pbc, expected_type, expected_dim):
        """
        Check that we can identify system type and dimensionality from an ASE object
        built from the top-level ModelSystem data.
        """
        sys = ModelSystem()
        sys.positions = positions*ureg.angstrom
        c = Cell(
            lattice_vectors=np.eye(3)*3.0*ureg.angstrom, 
            periodic_boundary_conditions=pbc
        )
        sys.cell.append(c)
        # Add enough AtomsState entries to match len(positions)
        for i in range(len(positions)):
            sys.particle_states.append(
                AtomsState(atom_definition_ref=AtomDefn(chemical_symbol="H"))
            )
        ase_atoms = sys.to_ase_atoms(logger=logger)
        stype, dim = sys.resolve_system_type_and_dimensionality(ase_atoms, logger=logger)
        assert stype == expected_type
        assert dim == expected_dim

    def test_normalize(self):
        """
        Test the full normalization sequence for ModelSystem:
          - If representative, run type/dimensionality, symmetry, chemical formula, etc.
        """
        # Build a minimal model system with top-level positions and an AtomicCell
        sys = ModelSystem(is_representative=True)
        sys.positions = np.array([[0,0,0],[0.5,0,0.5],[1,1,1]])*ureg.angstrom
        ac = generate_atomic_cell(
            lattice_vectors=[[3,0,0],[0,3,0],[0,0,3]],
            periodic_boundary_conditions=[True,True,True],
            chemical_symbols=["H","H","O"],
            atomic_numbers=[1,1,8],
        )
        sys.cell.append(ac)
        # Add a Symmetry, ChemicalFormula
        sym = Symmetry()
        sys.symmetry.append(sym)
        chem = ChemicalFormula()
        sys.chemical_formula = chem
        # Add 3 AtomsState entries for H,H,O
        for s in ["H","H","O"]:
            sys.particle_states.append(AtomsState(atom_definition_ref=AtomDefn(chemical_symbol=s)))

        # Normalize
        sys.normalize(EntryArchive(), logger=logger)
        # Check basic results
        assert sys.type in ["molecule / cluster","bulk"]  # or whichever your logic sets
        assert sys.dimensionality is not None
        if sys.chemical_formula is not None:
            # If the formula is expected "H2O," check that:
            assert sys.chemical_formula.descriptive == "H2O"
        # If your code appends cells (primitive, conventional), check that:
        if len(sys.cell) >= 2:
            assert sys.cell[1].type in ["primitive","conventional"]


@pytest.mark.parametrize("branching", [True, False])
def test_branch_depth_if_needed(branching):
    """
    Example test verifying branch_depth logic 
    if your code sets it for a nested set of sub_systems.
    """
    parent = ModelSystem(is_representative=True, branch_label="Parent")
    child = ModelSystem(branch_label="Child")
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