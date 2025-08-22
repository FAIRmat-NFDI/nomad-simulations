import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_system import (
    AtomicCell,
    ModelSystem,
)

from . import logger


class TestSimulation:
    """
    Test the `Simulation` class defined in general.py
    """

    @pytest.mark.parametrize(
        'system, result',
        [
            ([ModelSystem(name='depth 0')], [0]),
            (
                [
                    ModelSystem(
                        name='depth 0',
                        sub_systems=[
                            ModelSystem(name='depth 1'),
                            ModelSystem(name='depth 1'),
                        ],
                    )
                ],
                [0, 1, 1],
            ),
            (
                [
                    ModelSystem(
                        name='depth 0',
                        sub_systems=[
                            ModelSystem(
                                name='depth 1',
                                sub_systems=[ModelSystem(name='depth 2')],
                            ),
                            ModelSystem(name='depth 1'),
                        ],
                    )
                ],
                [0, 1, 2, 1],
            ),
        ],
    )
    def test_set_system_branch_depth(
        self, system: list[ModelSystem], result: list[int]
    ):
        """
        Test the `_set_system_branch_depth` method.

        Args:
            system (list[ModelSystem]): The system hierarchy to set the branch depths for.
            result (list[int]): The expected branch depths for each system in the hierarchy.
        """
        simulation = Simulation(model_system=system)
        for system_parent in simulation.model_system:
            system_parent.branch_depth = 0
            if len(system_parent.sub_systems) == 0:
                continue
            simulation._set_system_branch_depth(system_parent=system_parent)

        # TODO move this into its own method to handle `ModelSystem` hierarchies (see below `get_system_recurs`)
        def get_flat_depths(system_parent: ModelSystem, quantity_name: str, value=None):
            if value is None:
                value = []
            for system_child in system_parent.sub_systems:
                val = getattr(system_child, quantity_name)
                value.append(val)
                get_flat_depths(
                    system_parent=system_child, quantity_name=quantity_name, value=value
                )
            return value

        value = get_flat_depths(
            system_parent=simulation.model_system[0],
            quantity_name='branch_depth',
            value=[0],
        )
        assert value == result

    @pytest.mark.parametrize(
        'is_representative, has_atom_indices, mol_label_list, n_mol_list, atom_labels_list, composition_formula_list, custom_formulas',
        [
            (
                True,
                True,
                ['H20'],
                [3],
                [['H', 'O', 'O']],
                ['group_H20(1)', 'H20(3)', 'H(1)O(2)', 'H(1)O(2)', 'H(1)O(2)'],
                [None, None, None, None, None],
            ),  # pure system
            # (
            #     False,
            #     True,
            #     ['H20'],
            #     [3],
            #     [['H', 'O', 'O']],
            #     [None, None, None, None, None],
            #     [None, None, None, None, None],
            # ),  # non-representative system
            (  # TODO - decide between tests above or below depending on scope of is_representative
                False,
                True,
                ['H20'],
                [3],
                [['H', 'O', 'O']],
                [
                    'group_H20(1)',
                    'H20(3)',
                    'H(1)O(2)',
                    'H(1)O(2)',
                    'H(1)O(2)',
                ],  # compute even if not representative
                [None, None, None, None, None],
            ),
            (
                True,
                True,
                [None],
                [3],
                [['H', 'O', 'O']],
                ['H(3)O(6)', 'H(3)O(6)', 'H(1)O(2)', 'H(1)O(2)', 'H(1)O(2)'],
                [None, None, None, None, None],
            ),  # missing branch labels
            (
                True,
                True,
                ['H20'],
                [3],
                [[None, None, None]],
                ['group_H20(1)', 'H20(3)', None, None, None],
                [None, None, None, None, None],
            ),  # missing atom labels
            (
                True,
                False,
                ['H20'],
                [3],
                [['H', 'O', 'O']],
                ['group_H20(1)', 'H20(3)', None, None, None],
                [None, None, None, None, None],
            ),  # missing atom indices
            (
                True,
                True,
                ['H20'],
                [3],
                [['H', 'O', 'O']],
                ['waters(1)', 'water_molecules(3)', 'H(1)O(2)', 'H(1)O(2)', 'H(1)O(2)'],
                ['waters(1)', 'water_molecules(3)', None, None, None],
            ),  # custom formulas
            (
                True,
                True,
                ['H20', 'Methane'],
                [5, 2],
                [['H', 'O', 'O'], ['C', 'H', 'H', 'H', 'H']],
                [
                    'group_H20(1)group_Methane(1)',
                    'H20(5)',
                    'H(1)O(2)',
                    'H(1)O(2)',
                    'H(1)O(2)',
                    'H(1)O(2)',
                    'H(1)O(2)',
                    'Methane(2)',
                    'C(1)H(4)',
                    'C(1)H(4)',
                ],
                [None, None, None, None, None, None, None, None, None, None],
            ),  # binary mixture
        ],
    )
    def test_system_hierarchy_for_molecules(
        self,
        is_representative: bool,
        has_atom_indices: bool,
        mol_label_list: list[str],
        n_mol_list: list[int],
        atom_labels_list: list[str],
        composition_formula_list: list[str],
        custom_formulas: list[str],
    ):
        """
        Test the `Simulation` normalization for obtaining `Model.System.composition_formula` for atoms and molecules.

        Args:
            is_representative (bool): Specifies if branch_depth = 0 is representative or not.
            If not representative, the composition formulas should not be generated.
            has_atom_indices (bool): Specifies if the atom_indices should be populated during parsing.
            Without atom_indices, the composition formulas for the deepest level of the hierarchy
            should not be populated.
            mol_label_list (list[str]): Molecule types for generating the hierarchy.
            n_mol_list (list[int]): Number of molecules for each molecule type. Should be same
            length as mol_label_list.
            atom_labels_list (list[str]): Atom labels for each molecule type. Should be same length as
            mol_label_list, with each entry being a list of corresponding atom labels.
            composition_formula_list (list[str]): Resulting composition formulas after normalization. The
            ordering is dictated by the recursive traversing of the hierarchy in get_system_recurs(),
            which follows each branch to its deepest level before moving to the next branch, i.e.,
        """

        ### Generate the system hierarchy
        simulation = Simulation()
        model_system = ModelSystem(is_representative=True)
        simulation.model_system.append(model_system)
        model_system.branch_label = 'Total System'
        model_system.is_representative = is_representative
        model_system.composition_formula = custom_formulas[0]
        ctr_comp = 1
        # Create an AtomicCell (cell geometry only)
        atomic_cell = AtomicCell()
        model_system.cell.append(atomic_cell)
        if has_atom_indices:
            model_system.particle_indices = np.empty(0, dtype=np.int32)

        # add the atoms to the ModelSystem's particle_states.
        for mol_label, n_mol, atom_labels in zip(
            mol_label_list, n_mol_list, atom_labels_list
        ):
            # Create a branch (group) for this molecule type.
            model_system_mol_group = ModelSystem()
            if has_atom_indices:
                model_system_mol_group.particle_indices = np.empty(0, dtype=np.int32)
            model_system_mol_group.branch_label = (
                f'group_{mol_label}' if mol_label is not None else None
            )
            model_system_mol_group.composition_formula = custom_formulas[ctr_comp]
            ctr_comp += 1
            model_system.sub_systems.append(model_system_mol_group)
            for _ in range(n_mol):
                # Create a branch for an individual molecule.
                model_system_mol = ModelSystem(branch_label=mol_label)
                model_system_mol.branch_label = mol_label
                model_system_mol.composition_formula = custom_formulas[ctr_comp]
                ctr_comp += 1
                model_system_mol_group.sub_systems.append(model_system_mol)
                # Add the corresponding atoms to the global atom list (particle_states)
                for atom_label in atom_labels:
                    if atom_label is not None:
                        # Instantiate directly with the chemical symbol
                        model_system.particle_states.append(
                            AtomsState(chemical_symbol=atom_label)
                        )
                n_atoms = len(model_system.particle_states)
                particle_indices = np.arange(n_atoms - len(atom_labels), n_atoms)
                if has_atom_indices:
                    model_system_mol.particle_indices = particle_indices
                    if model_system_mol_group.particle_indices is None:
                        model_system_mol_group.particle_indices = particle_indices
                    else:
                        model_system_mol_group.particle_indices = np.append(
                            model_system_mol_group.particle_indices, particle_indices
                        )
                    if model_system.particle_indices is None:
                        model_system.particle_indices = particle_indices
                    else:
                        model_system.particle_indices = np.append(
                            model_system.particle_indices, particle_indices
                        )

        simulation.normalize(EntryArchive(), logger)

        ### Traverse the hierarchy recursively and check the results
        assert model_system.composition_formula == composition_formula_list[0]
        ctr_comp = 1

        # TODO move this into its own method to handle `ModelSystem` hierarchies (see above `get_flat_depths`)
        def get_system_recurs(systems: list[ModelSystem], ctr_comp: int) -> int:
            for sys in systems:
                assert sys.composition_formula == composition_formula_list[ctr_comp]
                ctr_comp += 1
                subsystems = sys.sub_systems
                if subsystems:
                    ctr_comp = get_system_recurs(subsystems, ctr_comp)
            return ctr_comp

        _ = get_system_recurs(systems=model_system.sub_systems, ctr_comp=ctr_comp)

    def test_root_leaf_composition_from_symbols_no_subsystems(self):
        """
        Root with no subsystems/particle_indices derives composition from its own symbols.
        """
        root = ModelSystem(is_representative=True)
        root.cell.append(AtomicCell())  # minimal cell so normalize doesn't bail
        for sym in ['H', 'H', 'O']:
            root.particle_states.append(AtomsState(chemical_symbol=sym))

        sim = Simulation(model_system=[root])
        sim.normalize(EntryArchive(), logger=logger)

        assert root.particle_indices is None  # root doesn't store indices
        assert root.composition_formula == 'H(2)O(1)'

    def test_root_leaf_custom_composition_preserved(self):
        """
        Pre-set custom composition on root is not overwritten during normalize.
        """
        root = ModelSystem(is_representative=True, composition_formula='Custom(1)')
        root.cell.append(AtomicCell())
        for sym in ['H', 'H', 'O']:
            root.particle_states.append(AtomsState(chemical_symbol=sym))

        sim = Simulation(model_system=[root])
        sim.normalize(EntryArchive(), logger=logger)

        assert root.composition_formula == 'Custom(1)'


@pytest.mark.parametrize(
    'initial_flags, expected_index, expected_flags',
    [
        # 1) zero representatives → promote last, index -1 (first pass)
        ([False, False, False], -1, [False, False, True]),
        # 2) multiple representatives → keep the last
        ([True, False, True, False], 2, [False, False, True, False]),
        # 3) exactly one representative → preserve it
        ([False, True, False], 1, [False, True, False]),
        # 4) singleton without representative → promote itself, index -1 (first pass)
        ([False], -1, [True]),
    ],
)
def test_representative_selection(initial_flags, expected_index, expected_flags):
    sim = Simulation(
        model_system=[
            ModelSystem(name=f'S{i}', is_representative=flag)
            for i, flag in enumerate(initial_flags)
        ]
    )

    # First pass: preserves the API’s special-casing (-1 means “last element”)
    sim.normalize(EntryArchive(), logger)
    assert sim.representative_system_index == expected_index
    assert [ms.is_representative for ms in sim.model_system] == expected_flags

    # Second pass: flags unchanged; index becomes canonical (non-negative)
    sim.normalize(EntryArchive(), logger)
    assert [ms.is_representative for ms in sim.model_system] == expected_flags
    expected_canonical_index = expected_flags.index(True)
    assert sim.representative_system_index == expected_canonical_index

    # Third pass: idempotent (no further changes)
    sim.normalize(EntryArchive(), logger)
    assert [ms.is_representative for ms in sim.model_system] == expected_flags
    assert sim.representative_system_index == expected_canonical_index
