import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    CGBeadState,
    ParticleState,
)
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_system import ModelSystem

from . import logger


class TestSimulationCGAndGeneric:
    """
    Tests for particle-agnostic composition resolution (atoms, CG beads, generic particles).
    NOTE: get_composition orders labels lexicographically (via np.unique), so expected
    strings below follow alphabetical ordering of labels.
    """

    @pytest.mark.parametrize(
        'particle_kinds, indices_sets, expected_leaf_formulas',
        [
            # Pure CG beads: bead_symbol, label, alt_labels (fallback). Indices pick C, C, A.
            (
                [
                    CGBeadState(bead_symbol='A'),
                    CGBeadState(label='B'),
                    CGBeadState(alt_labels=['C']),
                ],
                [[2, 2, 0]],
                ['A(1)C(2)'],  # lex order: A < C
            ),
            # Generic ParticleState only (no chemistry)
            (
                [ParticleState(label='monomer')] * 3,
                [[0, 0, 0]],
                ['monomer(3)'],
            ),
            # Mixed atoms + beads: H, B, O; indices pick H, O, B, O
            (
                [
                    AtomsState(chemical_symbol='H'),
                    CGBeadState(bead_symbol='B'),
                    AtomsState(chemical_symbol='O'),
                ],
                [[0, 2, 1, 2]],
                ['B(1)H(1)O(2)'],  # lex order: B < H < O
            ),
        ],
    )
    def test_particle_label_resolution(
        self, particle_kinds, indices_sets, expected_leaf_formulas
    ):
        sim = Simulation()
        root = ModelSystem(is_representative=True, branch_label='root')
        sim.model_system.append(root)

        # Populate global particle list
        for p in particle_kinds:
            root.particle_states.append(p)

        # Create leaves that reference global particle_indices
        for idxs, expected in zip(indices_sets, expected_leaf_formulas):
            leaf = ModelSystem(branch_label=None)
            leaf.particle_indices = np.array(idxs, dtype=int)
            root.sub_systems.append(leaf)

        sim.normalize(EntryArchive(), logger)

        # Verify leaf composition formulas (string comparison; order is lexicographic)
        for leaf, expected in zip(root.sub_systems, expected_leaf_formulas):
            assert leaf.composition_formula == expected


def test_qc_atomistic_no_cell():
    sim = Simulation()
    root = ModelSystem(is_representative=True, branch_label='root')
    sim.model_system.append(root)

    for s in ['H', 'O', 'H']:
        root.particle_states.append(AtomsState(chemical_symbol=s))

    leaf = ModelSystem()
    leaf.particle_indices = np.array([0, 1, 2], dtype=int)
    root.sub_systems.append(leaf)

    sim.normalize(EntryArchive(), logger)
    assert leaf.composition_formula == 'H(2)O(1)'
