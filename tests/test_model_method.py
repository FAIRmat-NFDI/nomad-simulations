from typing import Optional

import pytest
from nomad.datamodel import EntryArchive
from nomad_simulations.schema_packages.atoms_state import AtomsState, ElectronicState, SphericalSymmetryState
from nomad_simulations.schema_packages.model_method import (
    TB,
    SlaterKoster,
    SlaterKosterBond,
    Wannier,
)
from nomad_simulations.schema_packages.model_system import AtomicCell, ModelSystem

from . import logger
from .conftest import generate_simulation


class TestTB:
    """
    Test the `TB` class defined in `model_method.py`.
    """

    @pytest.mark.parametrize(
        'tb_section, result',
        [
            (Wannier(), 'Wannier'),
            (SlaterKoster(), 'SlaterKoster'),
            (TB(), None),
        ],
    )
    def test_resolve_type(self, tb_section: TB, result: str | None):
        """
        Test the `resolve_type` method of `TB`.
        E.g., Wannier => "Wannier", SlaterKoster => "SlaterKoster", TB => None.
        """
        assert tb_section.resolve_type() == result

    @pytest.mark.parametrize(
        'model_systems, model_index, result',
        [
            # (1) no `ModelSystem` sections
            ([], 0, None),
            # (2) `model_index` out of range
            ([ModelSystem()], 1, None),
            # (3) no `is_representative` in `ModelSystem`
            ([ModelSystem(is_representative=False)], 0, None),
            # (4) no `cell` section in `ModelSystem`
            ([ModelSystem(is_representative=True)], 0, None),
            # (5) no `particle_states` in `ModelSystem` – so no orbitals
            ([ModelSystem(is_representative=True, cell=[AtomicCell()])], 0, None),
            # (6) no child systems in `model_system`
            (
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        # no sub_systems, so can't find an 'active_atom' child
                    )
                ],
                0,
                None,
            ),
            # (7) child system type != 'active_atom'
            (
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        sub_systems=[ModelSystem(type='bulk')],
                    )
                ],
                0,
                None,
            ),
            # (8) child system is 'active_atom' but references a missing index in particle_states
            (
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        sub_systems=[
                            ModelSystem(type='active_atom', particle_indices=[2])
                        ],
                        particle_states=[AtomsState()],
                    )
                ],
                0,
                [],
            ),
            # (9) child system is 'active_atom' but that index has no orbitals_state
            (
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        particle_states=[AtomsState(orbitals_state=[])],
                        sub_systems=[
                            ModelSystem(type='active_atom', particle_indices=[0])
                        ],
                    )
                ],
                0,
                [],
            ),
            # Commented out for now.
            # (10) valid case with a single orbital
            # (
            #     [ModelSystem(
            #         is_representative=True,
            #         cell=[AtomicCell()],
            #         particle_states=[
            #             AtomsState(
            #                 orbitals_state=[OrbitalsState(l_quantum_symbol='s')])
            #         ],
            #         sub_systems=[ModelSystem(type='active_atom', particle_indices=[0])]
            #     )],
            #     0,
            #     [OrbitalsState(l_quantum_symbol='s')],
            #     #[],
            # ),
        ],
    )
    def test_resolve_orbital_references(
        self,
        model_systems: list[ModelSystem],
        model_index: int,
        result: list[ElectronicState] | None,
    ):
        """
        Test the `resolve_orbital_references` method of TB to find `ElectronicState` objects
        from a model_system child typed 'active_atom'.
        """
        tb_method = TB()
        simulation = generate_simulation(model_method=[tb_method])
        simulation.model_system = model_systems
        orbitals_ref = tb_method.resolve_orbital_references(
            model_systems=model_systems,
            logger=logger,
            model_index=model_index,
        )
        if not orbitals_ref:
            # Expect None or an empty list if not found
            assert orbitals_ref == result
        else:
            assert len(orbitals_ref) == len(result)
            if result and orbitals_ref:
                # Compare first electronic states for convenience
                assert orbitals_ref[0].name == result[0].name

    @pytest.mark.parametrize(
    'tb_section, result_type, model_systems, expected_states',
        [
            # (1) no method `type` extracted + no model systems
            (TB(), 'unavailable', [], None),
            # (2) method `type` extracted but no model systems
            (Wannier(), 'Wannier', [], None),
            # (3) representative system missing => no orbitals
            (Wannier(), 'Wannier', [ModelSystem(is_representative=False)], None),
            # (4) no cell
            (Wannier(), 'Wannier', [ModelSystem(is_representative=True)], None),
            # (5) no particle_states => no orbitals
            (
                Wannier(),
                'Wannier',
                [ModelSystem(is_representative=True, cell=[AtomicCell()])],
                None,
            ),
            # (6) sub_system with type != 'active_atom'
            (
                Wannier(),
                'Wannier',
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        sub_systems=[ModelSystem(type='bulk')],
                    )
                ],
                None,
            ),
            # (7) child system is 'active_atom' but references missing index
            (
                Wannier(),
                'Wannier',
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        sub_systems=[
                            ModelSystem(type='active_atom', particle_indices=[99])
                        ],
                        particle_states=[AtomsState(electronic_state=ElectronicState(name='missing_index_state', basis_orbitals=[SphericalSymmetryState()]))],
                    )
                ],
                None,
            ),
            # (8) child system is 'active_atom' but that index has no orbitals
            (
                Wannier(),
                'Wannier',
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        sub_systems=[
                            ModelSystem(type='active_atom', particle_indices=[0])
                        ],
                        particle_states=[AtomsState()],
                    )
                ],
                None,
            ),
            # (9) user gave Wannier.orbitals_ref => skip resolution
            (
                Wannier(orbitals_ref=[ElectronicState(name='user_orbital_state', basis_orbitals=[SphericalSymmetryState(l_quantum_symbol='p')])]),
                'Wannier',
                [ModelSystem(is_representative=True, cell=[AtomicCell()])],
                [ElectronicState(name='user_orbital_state', basis_orbitals=[SphericalSymmetryState(l_quantum_symbol='p')])],
            ),
            # Commented out for now.
            # (10) fully valid => single orbital
            # (
            #     Wannier(),
            #     'Wannier',
            #     [ModelSystem(
            #         is_representative=True,
            #         cell=[AtomicCell()],
            #         particle_states=[AtomsState(orbitals_state=[OrbitalsState(l_quantum_symbol='s')])],
            #         sub_systems=[ModelSystem(type='active_atom', particle_indices=[0])]
            #     )],
            #     [OrbitalsState(l_quantum_symbol='s')]
            # ),
        ],
    )
    def test_normalize(
        self,
        tb_section: TB,
        result_type: str,
        model_systems: list[ModelSystem],
        expected_states: list[ElectronicState] | None,
    ):
        """
        Test TB.normalize() [including Wannier or SlaterKoster],
        checking that it sets .type and .electronic_state_ref as needed.
        """
        # Attach the TB (or Wannier, or SlaterKoster) to a simulation
        sim = generate_simulation(model_method=[tb_section])
        sim.model_system = model_systems
        tb_section.normalize(EntryArchive(), logger=logger)
        # Check the recognized type
        assert tb_section.type == result_type
        if expected_states is None:
            assert tb_section.orbitals_ref is None or tb_section.orbitals_ref == []
        else:
            # Compare the first electronic states
            assert len(tb_section.orbitals_ref) == len(expected_states)
            for i, state in enumerate(expected_states):
                assert tb_section.orbitals_ref[i].name == state.name


class TestWannier:
    """
    Test the `Wannier` class specifically.
    """

    @pytest.mark.parametrize(
        'localization_type, is_maximally_localized, expected_type',
        [
            (None, None, None),
            ('single_shot', None, 'single_shot'),
            (None, True, 'maximally_localized'),
            (None, False, 'single_shot'),
        ],
    )
    def test_normalize(
        self,
        localization_type: str | None,
        is_maximally_localized: bool,
        expected_type: str | None,
    ):
        """
        Test that Wannier.normalize() sets the correct localization_type
        from is_maximally_localized if needed.
        """
        w = Wannier(
            localization_type=localization_type,
            is_maximally_localized=is_maximally_localized,
        )
        w.normalize(EntryArchive(), logger=logger)
        assert w.localization_type == expected_type


class TestSlaterKosterBond:
    """
    Test the `SlaterKosterBond` class.
    """

    @pytest.mark.parametrize(
        'orb1_symbol, orb2_symbol, bravais_vector, expected_name',
        [
            (None, None, None, None),
            ('s', None, None, None),
            (None, 'p', None, None),
            ('s', 's', (0, 0, 0), 'sss'),
            ('s', 'p', (0, 0, 0), 'sps'),
        ],
    )
    def test_resolve_bond_name_from_references(
        self,
        orb1_symbol: str | None,
        orb2_symbol: str | None,
        bravais_vector: tuple | None,
        expected_name: str | None,
    ):
        """
        Test SlaterKosterBond.resolve_bond_name_from_references with sample orbitals.
        """
        sk_bond = SlaterKosterBond()
        # If there's an orbit1 or orbit2, build them
        orbit1 = None
        if orb1_symbol:
            spherical_state = SphericalSymmetryState(l_quantum_symbol=orb1_symbol)
            orbit1 = ElectronicState(spin_orbit_state=spherical_state)
        
        orbit2 = None
        if orb2_symbol:
            spherical_state = SphericalSymmetryState(l_quantum_symbol=orb2_symbol)
            orbit2 = ElectronicState(spin_orbit_state=spherical_state)
            
        name = sk_bond.resolve_bond_name_from_references(
            orbital_1=orbit1,
            orbital_2=orbit2,
            bravais_vector=bravais_vector,
            logger=logger,
        )
        assert name == expected_name

    @pytest.mark.parametrize(
        'orb1_symbol, orb2_symbol, bravais_vector, expected',
        [
            (None, None, None, None),
            ('s', None, None, None),
            ('s', 'p', (0, 0, 0), 'sps'),
        ],
    )
    def test_normalize(
        self,
        orb1_symbol: str | None,
        orb2_symbol: str | None,
        bravais_vector: tuple | None,
        expected: str | None,
    ):
        """
        Test SlaterKosterBond.normalize() sets .name as we expect based on the orbitals.
        """
        # Prepare a model scenario
        bond = SlaterKosterBond()
        orbitals = []
        if orb1_symbol:
            spherical_state = SphericalSymmetryState(l_quantum_symbol=orb1_symbol)
            electronic_state = ElectronicState(spin_orbit_state=spherical_state)
            orbitals.append(electronic_state)
            bond.orbital_1 = orbitals[-1]
        if orb2_symbol:
            spherical_state = SphericalSymmetryState(l_quantum_symbol=orb2_symbol)
            electronic_state = ElectronicState(spin_orbit_state=spherical_state)
            orbitals.append(electronic_state)
            bond.orbital_2 = orbitals[-1]

        if bravais_vector is not None:
            bond.bravais_vector = bravais_vector

        bond.normalize(EntryArchive(), logger=logger)
        assert bond.name == expected
