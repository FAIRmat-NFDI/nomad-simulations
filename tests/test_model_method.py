import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    ElectronicState,
    SphericalSymmetryState,
)
from nomad_simulations.schema_packages.model_method import (
    DFT,
    TB,
    ExplicitDispersionModel,
    ImplicitSolvationModel,
    RelativityModel,
    SlaterKoster,
    SlaterKosterBond,
    Wannier,
    XCComponent,
    XCFunctional,
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
            # (10) valid case with single H atom with 1s orbital
            (
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        particle_states=[
                            AtomsState(
                                chemical_symbol='H',
                                electronic_state=ElectronicState(
                                    basis_orbitals=[
                                        SphericalSymmetryState(l_quantum_number=0)
                                    ]
                                ),
                            )
                        ],
                        sub_systems=[
                            ModelSystem(type='active_atom', particle_indices=[0])
                        ],
                    )
                ],
                0,
                # TODO: This should be a reference to the same ElectronicState instance
                # created above in particle_states[0].electronic_state
                [
                    ElectronicState(
                        basis_orbitals=[SphericalSymmetryState(l_quantum_number=0)]
                    )
                ],
            ),
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
        orbitals_ref = TB().resolve_orbital_references(
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
                        particle_states=[
                            AtomsState(
                                electronic_state=ElectronicState(
                                    name='missing_index_state',
                                    basis_orbitals=[SphericalSymmetryState()],
                                )
                            )
                        ],
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
                Wannier(
                    orbitals_ref=[
                        ElectronicState(
                            name='user_orbital_state',
                            basis_orbitals=[SphericalSymmetryState(l_quantum_number=1)],
                        )
                    ]
                ),
                'Wannier',
                [ModelSystem(is_representative=True, cell=[AtomicCell()])],
                [
                    ElectronicState(
                        name='user_orbital_state',
                        basis_orbitals=[SphericalSymmetryState(l_quantum_number=1)],
                    )
                ],
            ),
            # (10) fully valid Wannier with single s orbital
            (
                Wannier(),
                'Wannier',
                [
                    ModelSystem(
                        is_representative=True,
                        cell=[AtomicCell()],
                        particle_states=[
                            AtomsState(
                                chemical_symbol='H',
                                electronic_state=ElectronicState(
                                    basis_orbitals=[
                                        SphericalSymmetryState(l_quantum_number=0)
                                    ]
                                ),
                            )
                        ],
                        sub_systems=[
                            ModelSystem(type='active_atom', particle_indices=[0])
                        ],
                    )
                ],
                # TODO: This should be a reference to the same ElectronicState instance
                # created above in particle_states[0].electronic_state
                [
                    ElectronicState(
                        basis_orbitals=[SphericalSymmetryState(l_quantum_number=0)]
                    )
                ],
            ),
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
        'orb1_l_number, orb2_l_number, bravais_vector, expected_name',
        [
            (None, None, None, None),
            (0, None, None, None),
            (None, 1, None, None),
            (0, 0, (0, 0, 0), 'sss'),
            (0, 1, (0, 0, 0), 'sps'),
        ],
    )
    def test_resolve_bond_name_from_references(
        self,
        orb1_l_number: int | None,
        orb2_l_number: int | None,
        bravais_vector: tuple | None,
        expected_name: str | None,
    ):
        """
        Test SlaterKosterBond.resolve_bond_name_from_references with sample orbitals.
        """
        sk_bond = SlaterKosterBond()
        # If there's an orbit1 or orbit2, build them
        orbit1 = None
        if orb1_l_number is not None:
            spherical_state = SphericalSymmetryState(l_quantum_number=orb1_l_number)
            orbit1 = ElectronicState(spin_orbit_state=spherical_state)

        orbit2 = None
        if orb2_l_number is not None:
            spherical_state = SphericalSymmetryState(l_quantum_number=orb2_l_number)
            orbit2 = ElectronicState(spin_orbit_state=spherical_state)

        name = sk_bond.resolve_bond_name_from_references(
            orbital_1=orbit1,
            orbital_2=orbit2,
            bravais_vector=bravais_vector,
            logger=logger,
        )
        assert name == expected_name

    @pytest.mark.parametrize(
        'orb1_l_number, orb2_l_number, bravais_vector, expected',
        [
            (None, None, None, None),
            (0, None, None, None),
            (0, 1, (0, 0, 0), 'sps'),
        ],
    )
    def test_normalize(
        self,
        orb1_l_number: int | None,
        orb2_l_number: int | None,
        bravais_vector: tuple | None,
        expected: str | None,
    ):
        """
        Test SlaterKosterBond.normalize() sets .name as we expect based on the orbitals.
        """
        # Prepare a model scenario
        bond = SlaterKosterBond()
        orbitals = []
        if orb1_l_number is not None:
            spherical_state = SphericalSymmetryState(l_quantum_number=orb1_l_number)
            electronic_state = ElectronicState(spin_orbit_state=spherical_state)
            orbitals.append(electronic_state)
            bond.orbital_1 = orbitals[-1]
        if orb2_l_number is not None:
            spherical_state = SphericalSymmetryState(l_quantum_number=orb2_l_number)
            electronic_state = ElectronicState(spin_orbit_state=spherical_state)
            orbitals.append(electronic_state)
            bond.orbital_2 = orbitals[-1]

        if bravais_vector is not None:
            bond.bravais_vector = bravais_vector

        bond.normalize(EntryArchive(), logger=logger)
        assert bond.name == expected


class TestDFT:
    """
    Tests for the LibXC-normalized DFT schema:
      - xc container creation
      - Jacob's ladder derivation from component families
      - α (exact-exchange) derivation only when unambiguous
    """

    def test_creates_empty_xc_container_if_missing(self):
        dft = DFT()
        assert dft.xc is None  # precondition
        dft.normalize(EntryArchive(), logger=logger)
        # Should create an empty XCFunctional
        assert dft.xc is not None
        assert isinstance(dft.xc, XCFunctional)
        # With no components => jacobs_ladder -> 'unavailable' and no alpha
        assert dft.jacobs_ladder == 'unavailable'
        assert dft.xc.global_exact_exchange is None

    @pytest.mark.parametrize(
        'families, expected_rung',
        [
            (['LDA'], 'LDA'),
            (['GGA'], 'GGA'),
            (['meta-GGA'], 'meta-GGA'),
            (['hybrid-GGA'], 'hybrid-GGA'),
            (['hybrid-meta-GGA'], 'hybrid-meta-GGA'),
            (['LDA', 'GGA'], 'GGA'),
            (['GGA', 'meta-GGA'], 'meta-GGA'),
            (['LDA', 'hybrid-GGA'], 'hybrid-GGA'),
            (['GGA', 'meta-GGA', 'hybrid-meta-GGA'], 'hybrid-meta-GGA'),
        ],
    )
    def test_jacobs_ladder_highest_family_wins(self, families, expected_rung):
        dft = DFT()
        dft.xc = XCFunctional(
            components=[
                XCComponent(
                    libxc_id=100 + i,
                    canonical_label=f'XC_FAKE_{i}',
                    display_name=f'Fake {i}',
                    family=fam,
                    kind='xc',
                    weight=1.0,
                )
                for i, fam in enumerate(families)
            ]
        )
        dft.normalize(EntryArchive(), logger=logger)
        assert dft.jacobs_ladder == expected_rung

    @pytest.mark.parametrize(
        'components, preset_alpha, expected_alpha',
        [
            pytest.param(  # single component provides alpha
                [
                    XCComponent(
                        libxc_id=501,
                        canonical_label='XC_HYB_GGA_XC_FAKE',
                        display_name='Fake Hybrid',
                        family='hybrid-GGA',
                        kind='xc',
                        fraction_exact_exchange=0.25,
                        weight=1.0,
                    )
                ],
                None,
                0.25,
                id='single-component-alpha',
            ),
            pytest.param(  # multiple components agree on alpha
                [
                    XCComponent(
                        libxc_id=601,
                        canonical_label='XC_HYB_GGA_XC_FAKE1',
                        display_name='Fake H1',
                        family='hybrid-GGA',
                        kind='xc',
                        fraction_exact_exchange=0.20,
                        weight=0.8,
                    ),
                    XCComponent(
                        libxc_id=602,
                        canonical_label='XC_HYB_GGA_XC_FAKE2',
                        display_name='Fake H2',
                        family='hybrid-GGA',
                        kind='xc',
                        fraction_exact_exchange=0.20,
                        weight=0.2,
                    ),
                ],
                None,
                0.20,
                id='agreeing-components-alpha',
            ),
            pytest.param(  # components conflict -> None
                [
                    XCComponent(
                        libxc_id=701,
                        canonical_label='XC_HYB_GGA_XC_FAKE1',
                        display_name='Fake H1',
                        family='hybrid-GGA',
                        kind='xc',
                        fraction_exact_exchange=0.25,
                    ),
                    XCComponent(
                        libxc_id=702,
                        canonical_label='XC_HYB_GGA_XC_FAKE2',
                        display_name='Fake H2',
                        family='hybrid-GGA',
                        kind='xc',
                        fraction_exact_exchange=0.20,
                    ),
                ],
                None,
                None,
                id='conflicting-components-alpha',
            ),
            pytest.param(  # preset alpha should not be overwritten
                [
                    XCComponent(
                        libxc_id=801,
                        canonical_label='XC_HYB_GGA_XC_FAKE',
                        display_name='Fake Hybrid',
                        family='hybrid-GGA',
                        kind='xc',
                        fraction_exact_exchange=0.25,
                    )
                ],
                0.33,
                0.33,
                id='preset-alpha-preserved',
            ),
        ],
    )
    def test_exact_exchange_mixing_factor_resolution(
        self, components, preset_alpha, expected_alpha
    ):
        dft = DFT()
        dft.xc = XCFunctional(
            components=components,
            global_exact_exchange=preset_alpha if preset_alpha is not None else None,
        )
        dft.normalize(EntryArchive(), logger=logger)

        if expected_alpha is None:
            assert dft.xc.global_exact_exchange is None
        else:
            assert dft.xc.global_exact_exchange == pytest.approx(expected_alpha)


def test_dft_contributions_solvation_dispersion_relativity_normalize():
    dft = DFT()

    ism = ImplicitSolvationModel(
        model='PCM',
        solvent='water',
        dielectric_constant=78.4,
        refractive_index=1.33,
    )
    edm = ExplicitDispersionModel(
        model='D3BJ',
        damping_function='BJ',
        s6=1.0,
        a1=0.40,
        a2=4.00,
    )
    rel = RelativityModel(
        level='two-component',
        approximation='X2C',
        dkh_order=None,
    )

    dft.m_add_sub_section(type(dft).contributions, ism)
    dft.m_add_sub_section(type(dft).contributions, edm)
    dft.m_add_sub_section(type(dft).contributions, rel)

    for c in dft.contributions:
        c.normalize(EntryArchive(), logger=logger)

    assert len(dft.contributions) == 3
    assert isinstance(dft.contributions[0], ImplicitSolvationModel)
    assert isinstance(dft.contributions[1], ExplicitDispersionModel)
    assert isinstance(dft.contributions[2], RelativityModel)

    assert (
        pytest.approx(dft.contributions[0].dielectric_constant_optical, rel=1e-12)
        == 1.33**2
    )
    assert dft.contributions[0].dielectric_constant == 78.4
    assert dft.contributions[0].solvent == 'water'

    assert dft.contributions[1].model == 'D3BJ'
    assert dft.contributions[1].damping_function == 'BJ'
    assert dft.contributions[1].s6 == 1.0
    assert dft.contributions[1].a1 == 0.40
    assert dft.contributions[1].a2 == 4.00

    assert dft.contributions[2].level == 'two-component'
    assert dft.contributions[2].approximation == 'X2C'
    assert dft.contributions[2].dkh_order is None


def test_solvation_derives_optical_eps_if_only_n_given():
    dft = DFT()
    ism = ImplicitSolvationModel(
        model='GBSA', dielectric_constant=20.0, refractive_index=1.50
    )

    dft.m_add_sub_section(type(dft).contributions, ism)
    ism.normalize(EntryArchive(), logger=logger)

    assert pytest.approx(ism.dielectric_constant_optical, rel=1e-12) == 1.50**2


def test_dft_expands_functional_key_into_components():
    dft = DFT()
    dft.xc = XCFunctional(functional_key='PBE')
    dft.normalize(EntryArchive(), logger=logger)
    assert dft.xc.components
    assert all(c.canonical_label for c in dft.xc.components)


def test_dft_functional_key_population_is_idempotent():
    dft = DFT()
    dft.xc = XCFunctional(functional_key='PBE')
    dft.normalize(EntryArchive(), logger=logger)
    n1 = len(dft.xc.components or [])
    dft.normalize(EntryArchive(), logger=logger)
    assert len(dft.xc.components or []) == n1


_COMMON_XC_CASES = [
    # ---------------- LDA ----------------
    ('LDA', 'LDA', ['XC_LDA_X', 'XC_LDA_C_PW', 'XC_LDA_C_PZ']),
    ('PW92', 'LDA', ['XC_LDA_C_PW']),
    ('PZ81', 'LDA', ['XC_LDA_C_PZ']),
    ('VWN', 'LDA', ['XC_LDA_C_VWN']),
    ('SVWN', 'LDA', ['XC_LDA_X', 'XC_LDA_C_VWN']),
    ('LSDA', 'LDA', ['XC_LDA_X', 'XC_LDA_C_VWN']),
    ('LDA+PW', 'LDA', ['XC_LDA_X', 'XC_LDA_C_PW']),
    # ---------------- GGA ----------------
    ('PBE', 'GGA', ['XC_GGA_X_PBE', 'XC_GGA_C_PBE']),
    ('PBEsol', 'GGA', ['XC_GGA_X_PBE_SOL', 'XC_GGA_C_PBE_SOL']),
    ('revPBE', 'GGA', ['XC_GGA_X_RPBE', 'XC_GGA_C_PBE']),
    ('RPBE', 'GGA', ['XC_GGA_X_RPBE', 'XC_GGA_C_PBE']),
    ('PW91', 'GGA', ['XC_GGA_X_PW91', 'XC_GGA_C_PW91']),
    ('BLYP', 'GGA', ['XC_GGA_X_B88', 'XC_GGA_C_LYP']),
    ('BP86', 'GGA', ['XC_GGA_X_B88', 'XC_GGA_C_P86']),
    ('BOP', 'GGA', ['XC_GGA_X_BOP', 'XC_GGA_C_PBE']),
    ('OLYP', 'GGA', ['XC_GGA_X_OPTX', 'XC_GGA_C_LYP']),
    ('PBEint', 'GGA', ['XC_GGA_X_PBEINT', 'XC_GGA_C_PBEINT']),
    ('SOGGA', 'GGA', ['XC_GGA_X_SOGGA', 'XC_GGA_C_SOGGA11']),
    ('SOGGA11', 'GGA', ['XC_GGA_X_SOGGA11', 'XC_GGA_C_SOGGA11']),
    ('SOGGA11-X', 'GGA', ['XC_GGA_X_SOGGA11']),
    ('revTCA', 'GGA', ['XC_GGA_C_REVTPSS']),  # often paired w/ TPSS family corrs
    ('mPW91', 'GGA', ['XC_GGA_X_MPW91', 'XC_GGA_C_PW91']),
    ('mPWPW', 'GGA', ['XC_GGA_X_MPW91', 'XC_GGA_C_PW91']),
    ('mPWLYP', 'GGA', ['XC_GGA_X_MPW91', 'XC_GGA_C_LYP']),
    ('PBEalpha', 'GGA', ['XC_GGA_X_PBE_A', 'XC_GGA_C_PBE']),
    ('rPBE', 'GGA', ['XC_GGA_X_RPBE', 'XC_GGA_C_PBE']),
    ('WC', 'GGA', ['XC_GGA_X_WC']),
    ('HTBS', 'GGA', ['XC_GGA_X_HTBS', 'XC_GGA_C_PBE']),
    ('PBE+XDM', 'GGA', ['XC_GGA_X_PBE', 'XC_GGA_C_PBE']),
    # ------------- meta-GGA --------------
    ('SCAN', 'meta-GGA', ['XC_MGGA_X_SCAN', 'XC_MGGA_C_SCAN']),
    ('r2SCAN', 'meta-GGA', ['XC_MGGA_X_R2SCAN', 'XC_MGGA_C_R2SCAN']),
    ('TPSS', 'meta-GGA', ['XC_MGGA_X_TPSS', 'XC_MGGA_C_TPSS']),
    ('revTPSS', 'meta-GGA', ['XC_MGGA_X_REVTPSS', 'XC_MGGA_C_TPSS']),
    ('M06-L', 'meta-GGA', ['XC_MGGA_C_M06_L', 'XC_MGGA_X_M06_L']),
    ('MN15-L', 'meta-GGA', ['XC_MGGA_X_MN15_L', 'XC_MGGA_C_MN15_L']),
    ('B97M-V', 'meta-GGA', ['XC_MGGA_X_B97M_V', 'XC_NLC_XC_VV10']),
    ('B97M-rV', 'meta-GGA', ['XC_MGGA_X_B97M_RV', 'XC_NLC_XC_RVV10']),
    ('SCAN-L', 'meta-GGA', ['XC_MGGA_X_SCANL', 'XC_MGGA_C_SCAN']),
    ('TPSSloc', 'meta-GGA', ['XC_MGGA_X_TPSS', 'XC_MGGA_C_TPSS']),
    ('PKZB', 'meta-GGA', ['XC_MGGA_X_PKZB', 'XC_MGGA_C_PKZB']),
    ('BRx', 'meta-GGA', ['XC_MGGA_X_BR89']),
    ('M11-L', 'meta-GGA', ['XC_MGGA_X_M11_L', 'XC_MGGA_C_M11_L']),
    # ------------- hybrid-GGA ------------
    ('PBE0', 'hybrid-GGA', ['XC_HYB_GGA_XC_PBEH', 'XC_HYB_GGA_XC_PBE0']),
    ('B3LYP', 'hybrid-GGA', ['XC_HYB_GGA_XC_B3LYP', 'XC_HYB_GGA_XC_B3LYPS']),
    ('B3PW91', 'hybrid-GGA', ['XC_HYB_GGA_XC_B3PW91']),
    ('B97-1', 'hybrid-GGA', ['XC_HYB_GGA_XC_B97_1']),
    ('B97-2', 'hybrid-GGA', ['XC_HYB_GGA_XC_B97_2']),
    ('PBEh', 'hybrid-GGA', ['XC_HYB_GGA_XC_PBEH']),
    ('O3LYP', 'hybrid-GGA', ['XC_HYB_GGA_XC_O3LYP']),
    ('X3LYP', 'hybrid-GGA', ['XC_HYB_GGA_XC_X3LYP']),
    ('mPW1PW', 'hybrid-GGA', ['XC_HYB_GGA_XC_MPW1PW']),
    ('mPW3PW', 'hybrid-GGA', ['XC_HYB_GGA_XC_MPW3PW']),
    ('BHandH', 'hybrid-GGA', ['XC_HYB_GGA_XC_BHANDH']),
    ('BHandHLYP', 'hybrid-GGA', ['XC_HYB_GGA_XC_BHANDHLYP']),
    ('HSE03', 'hybrid-GGA', ['XC_HYB_GGA_XC_HSE03', 'XC_HYB_GGA_XC_HJS_PBE']),
    ('HSE06', 'hybrid-GGA', ['XC_HYB_GGA_XC_HSE06', 'XC_HYB_GGA_XC_HJS_PBE']),
    ('CAM-B3LYP', 'hybrid-GGA', ['XC_HYB_GGA_XC_CAM_B3LYP']),
    ('CAMB3LYP', 'hybrid-GGA', ['XC_HYB_GGA_XC_CAM_B3LYP']),
    ('LC-ωPBE', 'hybrid-GGA', ['XC_HYB_GGA_XC_LC_WPBE']),
    ('ωPBEh', 'hybrid-GGA', ['XC_HYB_GGA_XC_WPBEH']),
    ('N12-SX', 'hybrid-GGA', ['XC_HYB_GGA_XC_N12_SX']),
    ('APFD', 'hybrid-GGA', ['XC_HYB_GGA_XC_APFD']),
    # ---------- hybrid-meta-GGA ----------
    ('M06', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_M06', 'XC_HYB_MGGA_C_M06']),
    ('M06-2X', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_M06_2X', 'XC_HYB_MGGA_C_M06_2X']),
    ('M08-HX', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_M08_HX', 'XC_HYB_MGGA_C_M08_HX']),
    ('M08-SO', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_M08_SO', 'XC_HYB_MGGA_C_M08_SO']),
    ('M11', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_M11', 'XC_HYB_MGGA_C_M11']),
    ('MN15', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_MN15', 'XC_HYB_MGGA_C_MN15']),
    ('SCAN0', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_SCAN0', 'XC_MGGA_C_SCAN']),
    ('ωB97X-D', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_WB97X_D']),
    ('ωB97X-V', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_WB97X_V', 'XC_NLC_XC_VV10']),
    ('ωB97M-V', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_WB97M_V', 'XC_NLC_XC_VV10']),
    # ('revM06-L (hyb-like)', 'hybrid-meta-GGA', ['XC_HYB_MGGA_X_M06', 'XC_MGGA_C_M06_L']), #this is a hack, not a real hybrid!
    # ----------- meta-GGA + NL combos ----
    (
        'SCAN + rVV10',
        'meta-GGA',
        ['XC_MGGA_X_SCAN', 'XC_NLC_XC_RVV10', 'XC_NLCF_XC_RVV10'],
    ),
    (
        'r2SCAN + VV10',
        'meta-GGA',
        ['XC_MGGA_X_R2SCAN', 'XC_NLC_XC_VV10', 'XC_NLCF_XC_VV10'],
    ),
    ('B97M-V (explicit)', 'meta-GGA', ['XC_MGGA_X_B97M_V', 'XC_NLC_XC_VV10']),
    ('B97M-rV (explicit)', 'meta-GGA', ['XC_MGGA_X_B97M_RV', 'XC_NLC_XC_RVV10']),
    ('TPSS + D3(BJ)', 'meta-GGA', ['XC_MGGA_X_TPSS', 'XC_MGGA_C_TPSS']),
    ('SCAN + D3(BJ)', 'meta-GGA', ['XC_MGGA_X_SCAN', 'XC_MGGA_C_SCAN']),
    ('r2SCAN + D4', 'meta-GGA', ['XC_MGGA_X_R2SCAN', 'XC_MGGA_C_R2SCAN']),
    # ------------- GGA + NL combos --------
    ('PBE + VV10', 'GGA', ['XC_GGA_X_PBE', 'XC_NLC_XC_VV10']),
    ('PBE + rVV10', 'GGA', ['XC_GGA_X_PBE', 'XC_NLC_XC_RVV10']),
    ('revPBE + VV10', 'GGA', ['XC_GGA_X_RPBE', 'XC_NLC_XC_VV10']),
    ('BLYP + VV10', 'GGA', ['XC_GGA_X_B88', 'XC_GGA_C_LYP', 'XC_NLC_XC_VV10']),
    ('PBE + D3(BJ)', 'GGA', ['XC_GGA_X_PBE', 'XC_GGA_C_PBE']),
    ('PBEsol + D3', 'GGA', ['XC_GGA_X_PBE_SOL', 'XC_GGA_C_PBE_SOL']),
    ('BP86 + D3', 'GGA', ['XC_GGA_X_B88', 'XC_GGA_C_P86']),
    # ------------- Hybrids + NL -----------
    ('B3LYP + D3(BJ)', 'hybrid-GGA', ['XC_HYB_GGA_XC_B3LYP']),
    ('PBE0 + D3(BJ)', 'hybrid-GGA', ['XC_HYB_GGA_XC_PBE0', 'XC_HYB_GGA_XC_PBEH']),
    ('HSE06 + D3(BJ)', 'hybrid-GGA', ['XC_HYB_GGA_XC_HSE06']),
    (
        'ωB97X-V (explicit)',
        'hybrid-meta-GGA',
        ['XC_HYB_MGGA_X_WB97X_V', 'XC_NLC_XC_VV10'],
    ),
    (
        'ωB97M-V (explicit)',
        'hybrid-meta-GGA',
        ['XC_HYB_MGGA_X_WB97M_V', 'XC_NLC_XC_VV10'],
    ),
    # -------- a few “code nicknames” ------
    ('PBE0 (alias PBEh)', 'hybrid-GGA', ['XC_HYB_GGA_XC_PBEH', 'XC_HYB_GGA_XC_PBE0']),
    ('HSE (generic)', 'hybrid-GGA', ['XC_HYB_GGA_XC_HSE06', 'XC_HYB_GGA_XC_HSE03']),
    ('B3PW', 'hybrid-GGA', ['XC_HYB_GGA_XC_B3PW91']),
]


@pytest.mark.parametrize('raw, expected_family, _labels', _COMMON_XC_CASES)
def test_dft_expands_100_common_functionals(raw, expected_family, _labels):
    dft = DFT()
    dft.xc = XCFunctional(functional_key=raw)
    dft.normalize(EntryArchive(), logger=logger)

    assert dft.xc.components, f'Expansion produced no components for {raw}'
    assert all(c.canonical_label for c in dft.xc.components)
    assert dft.jacobs_ladder == expected_family

    if expected_family.startswith('hybrid'):
        # Schema must not infer α from names
        assert dft.xc.global_exact_exchange is None


@pytest.mark.parametrize('raw', ['PBE', 'B3LYP', 'HSE06', 'SCAN+rVV10'])
def test_dft_expansion_is_idempotent_for_common_functionals(raw):
    dft = DFT()
    dft.xc = XCFunctional(functional_key=raw)
    dft.normalize(EntryArchive(), logger=logger)
    n1 = len(dft.xc.components or [])
    dft.normalize(EntryArchive(), logger=logger)
    n2 = len(dft.xc.components or [])
    assert n2 == n1
