import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    ElectronicState,
    SphericalSymmetryState,
)
from nomad_simulations.schema_packages.model_method import (
    BSDFT,
    CC,
    DFT,
    TB,
    ActiveSpace,
    BrokenSymmetryCenter,
    EmpiricalDispersionModel,
    ImplicitSolvationModel,
    LocalCorrelation,
    LocalCorrelationSpace,
    MultireferencePT,
    MultireferenceSCF,
    NonlocalCorrelation,
    OrbitalLocalization,
    RelativityModel,
    SelfInteractionCorrection,
    SlaterKoster,
    SlaterKosterBond,
    Wannier,
    XCComponent,
    XCFunctional,
)
from nomad_simulations.schema_packages.model_system import ModelSystem, Representation
from nomad_simulations.schema_packages.numerical_settings import (
    LocalCorrelationSettings,
    LocalCorrelationThreshold,
)

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
            (
                [
                    ModelSystem(
                        is_representative=True, representations=[Representation()]
                    )
                ],
                0,
                None,
            ),
            # (6) no child systems in `model_system`
            (
                [
                    ModelSystem(
                        is_representative=True,
                        representations=[Representation()],
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
                        representations=[Representation()],
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
                        representations=[Representation()],
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
                        representations=[Representation()],
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
                        representations=[Representation()],
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
                [
                    ModelSystem(
                        is_representative=True, representations=[Representation()]
                    )
                ],
                None,
            ),
            # (6) sub_system with type != 'active_atom'
            (
                Wannier(),
                'Wannier',
                [
                    ModelSystem(
                        is_representative=True,
                        representations=[Representation()],
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
                        representations=[Representation()],
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
                        representations=[Representation()],
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
                [
                    ModelSystem(
                        is_representative=True, representations=[Representation()]
                    )
                ],
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
                        representations=[Representation()],
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


class TestMultireferenceMethods:
    def test_multireference_scf_normalize_sets_state_groups(self):
        active = ActiveSpace(n_active_orbitals=4, n_active_electrons=6)
        mref = MultireferenceSCF(
            type='CASSCF',
            reference_type='state_averaged',
            state_multiplicities=[3, 1],
            n_roots_per_multiplicity=[2, 3],
            active_space=active,
        )

        mref.normalize(EntryArchive(), logger=logger)

        assert mref.n_state_groups == 2
        assert mref.active_space is active
        assert list(mref.state_multiplicities) == [3, 1]
        assert list(mref.n_roots_per_multiplicity) == [2, 3]


def build_local_correlation_space(**overrides) -> LocalCorrelationSpace:
    space_kwargs = {
        'kind': 'domain',
        'domain_kind': 'pair',
        'excitation_order': 2,
    }
    space_kwargs.update(overrides)
    return LocalCorrelationSpace(**space_kwargs)


def build_local_correlation(
    local_type: str = 'DLPNO',
    spaces: list[LocalCorrelationSpace] | None = None,
    localization: OrbitalLocalization | None = None,
) -> LocalCorrelation:
    return LocalCorrelation(
        type=local_type,
        orbital_localization_ref=localization,
        spaces=spaces
        or [
            build_local_correlation_space(
                kind='orbital',
                domain_kind=None,
                virtual_space_type='PNO',
                excitation_order=2,
            )
        ],
    )


class TestCC:
    def test_cc_stores_local_correlation_subsection(self):
        localization = OrbitalLocalization(
            method='Pipek-Mezey',
            n_localized_orbitals=12,
        )
        occ_i = ElectronicState(name='i')
        occ_j = ElectronicState(name='j')
        occ_k = ElectronicState(name='k')
        pno_1 = ElectronicState(name='pno_1')
        pno_2 = ElectronicState(name='pno_2')
        local_corr = build_local_correlation(
            localization=localization,
            spaces=[
                build_local_correlation_space(
                    kind='domain',
                    domain_kind='pair',
                    excitation_order=2,
                    defining_orbitals_ref=[occ_i, occ_j],
                ),
                build_local_correlation_space(
                    kind='orbital',
                    domain_kind=None,
                    virtual_space_type='PNO',
                    excitation_order=2,
                    defining_orbitals_ref=[occ_i, occ_j],
                    orbitals_ref=[pno_1, pno_2],
                ),
                build_local_correlation_space(
                    kind='orbital',
                    domain_kind=None,
                    virtual_space_type='PNO',
                    excitation_order=3,
                    defining_orbitals_ref=[occ_i, occ_j, occ_k],
                ),
            ],
        )
        local_corr_settings = LocalCorrelationSettings(
            screening_thresholds=[
                LocalCorrelationThreshold(
                    name='TCutPairs',
                    value=1.0e-4,
                    applies_to='pair_screening',
                ),
                LocalCorrelationThreshold(
                    name='TCutPNO',
                    value=1.0e-8,
                    applies_to='orbital',
                ),
            ]
        )
        cc = CC(
            type='CCSD',
            excitation_order=[1, 2],
            perturbative_correction='(T)',
            perturbative_correction_order=[3],
            local_correlation=local_corr,
            numerical_settings=[local_corr_settings],
        )

        assert cc.local_correlation is local_corr
        assert cc.local_correlation.type == 'DLPNO'
        assert cc.local_correlation.orbital_localization_ref is localization
        assert len(cc.local_correlation.spaces) == 3
        assert cc.local_correlation.spaces[0].kind == 'domain'
        assert cc.local_correlation.spaces[0].domain_kind == 'pair'
        assert cc.local_correlation.spaces[1].virtual_space_type == 'PNO'
        assert list(cc.local_correlation.spaces[0].defining_orbitals_ref) == [
            occ_i,
            occ_j,
        ]
        assert list(cc.local_correlation.spaces[1].orbitals_ref) == [pno_1, pno_2]
        assert cc.local_correlation.spaces[2].excitation_order == 3
        assert len(cc.numerical_settings) == 1
        assert isinstance(cc.numerical_settings[0], LocalCorrelationSettings)
        assert len(cc.numerical_settings[0].screening_thresholds) == 2
        assert cc.numerical_settings[0].screening_thresholds[0].name == 'TCutPairs'
        assert cc.numerical_settings[0].screening_thresholds[1].value == pytest.approx(
            1.0e-8
        )

    @pytest.mark.parametrize(
        'local_type, space_type',
        [
            ('LNO', 'LNO'),
            ('PNO', 'PNO'),
            ('LPNO', 'PNO'),
            ('DLPNO', 'PNO'),
        ],
    )
    def test_cc_local_correlation_supports_generic_local_cc_families(
        self, local_type: str, space_type: str
    ):
        cc = CC(
            type='CCSD',
            local_correlation=build_local_correlation(
                local_type=local_type,
                spaces=[
                    build_local_correlation_space(
                        kind='orbital',
                        domain_kind=None,
                        virtual_space_type=space_type,
                        excitation_order=2,
                    )
                ],
            ),
        )

        assert cc.local_correlation is not None
        assert cc.local_correlation.type == local_type
        assert len(cc.local_correlation.spaces) == 1
        assert cc.local_correlation.spaces[0].virtual_space_type == space_type

    def test_local_correlation_space_supports_orbital_domain(self):
        space = build_local_correlation_space(
            kind='domain',
            domain_kind='orbital',
            excitation_order=1,
        )

        assert space.domain_kind == 'orbital'

    def test_local_correlation_space_supports_quadruples_order(self):
        space = build_local_correlation_space(
            kind='orbital',
            domain_kind=None,
            virtual_space_type='PNO',
            excitation_order=4,
        )

        assert space.excitation_order == 4

    def test_local_correlation_space_normalize_sets_counts_from_references(self):
        occ_i = ElectronicState(name='i')
        occ_j = ElectronicState(name='j')
        pno_1 = ElectronicState(name='pno_1')
        pno_2 = ElectronicState(name='pno_2')

        space = build_local_correlation_space(
            kind='orbital',
            domain_kind=None,
            virtual_space_type='PNO',
            defining_orbitals_ref=[occ_i, occ_j],
            orbitals_ref=[pno_1, pno_2],
        )

        space.normalize(EntryArchive(), logger=logger)

        assert space.n_defining_orbitals == 2
        assert space.n_orbitals == 2

    def test_local_correlation_space_normalize_validates_domain_kind_cardinality(
        self, caplog
    ):
        import logging

        space = build_local_correlation_space(
            kind='domain',
            domain_kind='pair',
            defining_orbitals_ref=[ElectronicState(name='i')],
        )

        with caplog.at_level(logging.WARNING):
            space.normalize(EntryArchive(), logger=logger)

        assert (
            'LocalCorrelationSpace.domain_kind `pair` expects 2 defining orbitals'
            in caplog.text
        )

    @pytest.mark.parametrize(
        'kwargs, expected_warning',
        [
            (
                {
                    'kind': 'domain',
                    'domain_kind': None,
                    'virtual_space_type': 'PNO',
                },
                'LocalCorrelationSpace.kind `domain` requires `domain_kind`.',
            ),
            (
                {
                    'kind': 'domain',
                    'virtual_space_type': 'PNO',
                },
                'LocalCorrelationSpace.kind `domain` must not define `virtual_space_type` (`PNO`).',
            ),
            (
                {
                    'kind': 'orbital',
                    'domain_kind': 'pair',
                    'virtual_space_type': None,
                },
                'LocalCorrelationSpace.kind `orbital` requires `virtual_space_type`.',
            ),
            (
                {
                    'kind': 'orbital',
                    'domain_kind': 'pair',
                    'virtual_space_type': 'PNO',
                },
                'LocalCorrelationSpace.kind `orbital` must not define `domain_kind` (`pair`).',
            ),
            (
                {
                    'kind': 'orbital',
                    'domain_kind': 'pair',
                    'virtual_space_type': 'PNO',
                },
                'LocalCorrelationSpace must not define both `domain_kind` and `virtual_space_type`.',
            ),
        ],
    )
    def test_local_correlation_space_normalize_validates_domain_orbital_fields(
        self, caplog, kwargs: dict[str, str | None], expected_warning: str
    ):
        import logging

        space = build_local_correlation_space(**kwargs)

        with caplog.at_level(logging.WARNING):
            space.normalize(EntryArchive(), logger=logger)

        assert expected_warning in caplog.text


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


class TestBSDFT:
    @staticmethod
    def _spin_centers(*ms_quantum_numbers: float | None) -> list[BrokenSymmetryCenter]:
        return [
            BrokenSymmetryCenter(
                atom_ref=AtomsState(chemical_symbol='Fe'),
                spin_state=(
                    SphericalSymmetryState(ms_quantum_number=ms_quantum_number)
                    if ms_quantum_number is not None
                    else None
                ),
            )
            for ms_quantum_number in ms_quantum_numbers
        ]

    def test_valid_bsdft_mixed_spin_centers(self, log_output):
        site_a = AtomsState(chemical_symbol='Fe', label='Fe1')
        site_b = AtomsState(chemical_symbol='Fe', label='Fe2')
        bsdft = BSDFT(
            determinant='unrestricted',
            is_spin_polarized=True,
            total_spin_projection=1,
            spin_centers=[
                BrokenSymmetryCenter(
                    atom_ref=site_a,
                    spin_state=SphericalSymmetryState(ms_quantum_number=0.5),
                    label='site_a',
                ),
                BrokenSymmetryCenter(
                    atom_ref=site_b,
                    spin_state=SphericalSymmetryState(ms_quantum_number=-0.5),
                    label='site_b',
                ),
            ],
        )

        bsdft.normalize(EntryArchive(), logger=logger)

        assert bsdft.name == 'BSDFT'
        assert bsdft.total_spin_projection == 1
        assert len(log_output.entries) == 0

    @pytest.mark.parametrize(
        'determinant, is_spin_polarized, ms_quantum_numbers, expected_event',
        [
            pytest.param(
                'restricted',
                True,
                (0.5, -0.5),
                'BSDFT requires `determinant` to be `unrestricted`.',
                id='restricted-determinant',
            ),
            pytest.param(
                None,
                True,
                (0.5, -0.5),
                'BSDFT requires `determinant` to be `unrestricted`.',
                id='missing-determinant',
            ),
            pytest.param(
                'unrestricted',
                False,
                (0.5, -0.5),
                'BSDFT requires `is_spin_polarized` to be `True`.',
                id='non-spin-polarized',
            ),
            pytest.param(
                'unrestricted',
                None,
                (0.5, -0.5),
                'BSDFT requires `is_spin_polarized` to be `True`.',
                id='missing-spin-polarization',
            ),
            pytest.param(
                'unrestricted',
                True,
                (0.5,),
                'BSDFT requires at least two `spin_centers` to define a broken-symmetry assignment.',
                id='too-few-spin-centers',
            ),
            pytest.param(
                'unrestricted',
                True,
                (0.5, 0.5),
                'BSDFT requires at least one up and one down spin center.',
                id='same-spin-sign',
            ),
            pytest.param(
                'unrestricted',
                True,
                (0.0, -0.5),
                'BSDFT `spin_centers` must provide a resolvable spin sign (e.g. via a '
                '`SphericalSymmetryState` `spin_state` with non-zero `ms_quantum_number`).',
                id='unresolvable-spin-sign',
            ),
        ],
    )
    def test_warns_on_invalid_bsdft_metadata(
        self,
        log_output,
        determinant,
        is_spin_polarized,
        ms_quantum_numbers,
        expected_event,
    ):
        bsdft = BSDFT(
            determinant=determinant,
            is_spin_polarized=is_spin_polarized,
            spin_centers=self._spin_centers(*ms_quantum_numbers),
        )

        bsdft.normalize(EntryArchive(), logger=logger)

        assert any(entry['event'] == expected_event for entry in log_output.entries)


def test_dft_contributions_solvation_dispersion_relativity_normalize():
    dft = DFT()

    ism = ImplicitSolvationModel(
        model='PCM',
        solvent='water',
        dielectric_constant=78.4,
        refractive_index=1.33,
    )

    edm = EmpiricalDispersionModel(
        model='D3BJ',
        damping_function='BJ',
    )

    rel = RelativityModel(
        level='two-component',
        approximation='X2C',
        dkh_order=None,
    )

    sic = SelfInteractionCorrection(
        method='EXPLICIT_ORBITALS',
        scaling_factor=0.5,
        corrected_orbitals_ref=[
            ElectronicState(name='orbital_1'),
            ElectronicState(name='orbital_2'),
        ],
    )

    dft.m_add_sub_section(type(dft).contributions, ism)
    dft.m_add_sub_section(type(dft).contributions, edm)
    dft.m_add_sub_section(type(dft).contributions, rel)
    dft.m_add_sub_section(type(dft).contributions, sic)

    for c in dft.contributions:
        c.normalize(EntryArchive(), logger=logger)

    assert len(dft.contributions) == 4
    assert isinstance(dft.contributions[0], ImplicitSolvationModel)
    assert isinstance(dft.contributions[1], EmpiricalDispersionModel)
    assert isinstance(dft.contributions[2], RelativityModel)
    assert isinstance(dft.contributions[3], SelfInteractionCorrection)

    # Solvation
    assert (
        pytest.approx(dft.contributions[0].dielectric_constant_optical, rel=1e-12)
        == 1.33**2
    )
    assert dft.contributions[0].dielectric_constant == 78.4
    assert dft.contributions[0].solvent == 'water'

    # Dispersion (method identity only in model_method.py tests)
    assert dft.contributions[1].model == 'D3BJ'
    assert dft.contributions[1].damping_function == 'BJ'

    # Relativity
    assert dft.contributions[2].level == 'two-component'
    assert dft.contributions[2].approximation == 'X2C'
    assert dft.contributions[2].dkh_order is None

    # Self-interaction correction
    assert dft.contributions[3].name == 'SIC'
    assert dft.contributions[3].method == 'EXPLICIT_ORBITALS'
    assert dft.contributions[3].correction_target == 'selected_orbitals'
    assert dft.contributions[3].scaling_factor == pytest.approx(0.5)
    assert dft.contributions[3].n_corrected_orbitals == 2


@pytest.mark.parametrize(
    'method, expected_target',
    [
        ('AD', 'average_density'),
        ('SOSEX', 'screened_exchange'),
        ('EXPLICIT_ORBITALS', 'selected_orbitals'),
        ('MAURI_SPZ', 'spin_density'),
        ('MAURI_US', 'doublet_unpaired_orbital'),
    ],
)
def test_self_interaction_correction_infers_target_from_method(method, expected_target):
    sic = SelfInteractionCorrection(method=method)
    sic.normalize(EntryArchive(), logger=logger)

    assert sic.name == 'SIC'
    assert sic.correction_target == expected_target


def test_self_interaction_correction_counts_corrected_orbitals():
    sic = SelfInteractionCorrection(
        method='EXPLICIT_ORBITALS',
        corrected_orbitals_ref=[
            ElectronicState(name='orbital_1'),
            ElectronicState(name='orbital_2'),
            ElectronicState(name='orbital_3'),
        ],
    )

    sic.normalize(EntryArchive(), logger=logger)

    assert sic.n_corrected_orbitals == 3


def test_solvation_derives_optical_eps_if_only_n_given():
    dft = DFT()
    ism = ImplicitSolvationModel(
        model='GBSA', dielectric_constant=20.0, refractive_index=1.50
    )

    dft.m_add_sub_section(type(dft).contributions, ism)
    ism.normalize(EntryArchive(), logger=logger)

    assert pytest.approx(ism.dielectric_constant_optical, rel=1e-12) == 1.50**2


def test_dft_sets_nonlocal_correlation_xc_partner_ref_when_missing():
    dft = DFT()
    dft.xc = XCFunctional(functional_key='PBE')
    nonlocal_corr = NonlocalCorrelation(type='VV10')
    dft.m_add_sub_section(type(dft).contributions, nonlocal_corr)

    dft.normalize(EntryArchive(), logger=logger)

    assert nonlocal_corr.xc_partner_ref is dft.xc


_COMMON_XC_CASES = [
    # ---------------- LDA ----------------
    ('LDA', 'LDA'),
    ('PW92', 'LDA'),
    ('PZ81', 'LDA'),
    ('VWN', 'LDA'),
    ('SVWN', 'LDA'),
    ('LSDA', 'LDA'),
    ('LDA+PW', 'LDA'),
    # ---------------- GGA ----------------
    ('PBE', 'GGA'),
    ('PBEsol', 'GGA'),
    ('revPBE', 'GGA'),
    ('RPBE', 'GGA'),
    ('PW91', 'GGA'),
    ('BLYP', 'GGA'),
    ('BP86', 'GGA'),
    ('BOP', 'GGA'),
    ('OLYP', 'GGA'),
    ('PBEint', 'GGA'),
    ('SOGGA', 'GGA'),
    ('SOGGA11', 'GGA'),
    ('SOGGA11-X', 'GGA'),
    ('revTCA', 'GGA'),  # often paired w/ TPSS family corrs
    ('mPW91', 'GGA'),
    ('mPWPW', 'GGA'),
    ('mPWLYP', 'GGA'),
    ('PBEalpha', 'GGA'),
    ('rPBE', 'GGA'),
    ('WC', 'GGA'),
    ('HTBS', 'GGA'),
    ('PBE+XDM', 'GGA'),
    # ------------- meta-GGA --------------
    ('SCAN', 'meta-GGA'),
    ('r2SCAN', 'meta-GGA'),
    ('TPSS', 'meta-GGA'),
    ('revTPSS', 'meta-GGA'),
    ('M06-L', 'meta-GGA'),
    ('MN15-L', 'meta-GGA'),
    ('B97M-V', 'meta-GGA'),
    ('B97M-rV', 'meta-GGA'),
    ('SCAN-L', 'meta-GGA'),
    ('TPSSloc', 'meta-GGA'),
    ('PKZB', 'meta-GGA'),
    ('BRx', 'meta-GGA'),
    ('M11-L', 'meta-GGA'),
    # ------------- hybrid-GGA ------------
    ('PBE0', 'hybrid-GGA'),
    ('B3LYP', 'hybrid-GGA'),
    ('B3PW91', 'hybrid-GGA'),
    ('B97-1', 'hybrid-GGA'),
    ('B97-2', 'hybrid-GGA'),
    ('PBEh', 'hybrid-GGA'),
    ('O3LYP', 'hybrid-GGA'),
    ('X3LYP', 'hybrid-GGA'),
    ('mPW1PW', 'hybrid-GGA'),
    ('mPW3PW', 'hybrid-GGA'),
    ('BHandH', 'hybrid-GGA'),
    ('BHandHLYP', 'hybrid-GGA'),
    ('HSE03', 'hybrid-GGA'),
    ('HSE06', 'hybrid-GGA'),
    ('CAM-B3LYP', 'hybrid-GGA'),
    ('CAMB3LYP', 'hybrid-GGA'),
    ('LC-ωPBE', 'hybrid-GGA'),
    ('ωPBEh', 'hybrid-GGA'),
    ('N12-SX', 'hybrid-GGA'),
    ('APFD', 'hybrid-GGA'),
    # ---------- hybrid-meta-GGA ----------
    ('M06', 'hybrid-meta-GGA'),
    ('M06-2X', 'hybrid-meta-GGA'),
    ('M08-HX', 'hybrid-meta-GGA'),
    ('M08-SO', 'hybrid-meta-GGA'),
    ('M11', 'hybrid-meta-GGA'),
    ('MN15', 'hybrid-meta-GGA'),
    ('SCAN0', 'hybrid-meta-GGA'),
    ('ωB97X-D', 'hybrid-GGA'),
    ('ωB97X-V', 'hybrid-GGA'),
    ('ωB97M-V', 'hybrid-meta-GGA'),
    # ('revM06-L (hyb-like)', 'hybrid-meta-GGA'), #this is a hack, not a real hybrid!
    # ----------- meta-GGA + NL combos ----
    ('SCAN + rVV10', 'meta-GGA'),
    ('r2SCAN + VV10', 'meta-GGA'),
    ('B97M-V (explicit)', 'meta-GGA'),
    ('B97M-rV (explicit)', 'meta-GGA'),
    ('TPSS + D3(BJ)', 'meta-GGA'),
    ('SCAN + D3(BJ)', 'meta-GGA'),
    ('r2SCAN + D4', 'meta-GGA'),
    # ------------- GGA + NL combos --------
    ('PBE + VV10', 'GGA'),
    ('PBE + rVV10', 'GGA'),
    ('revPBE + VV10', 'GGA'),
    ('BLYP + VV10', 'GGA'),
    ('PBE + D3(BJ)', 'GGA'),
    ('PBEsol + D3', 'GGA'),
    ('BP86 + D3', 'GGA'),
    # ------------- Hybrids + NL -----------
    ('B3LYP + D3(BJ)', 'hybrid-GGA'),
    ('PBE0 + D3(BJ)', 'hybrid-GGA'),
    ('HSE06 + D3(BJ)', 'hybrid-GGA'),
    ('ωB97X-V (explicit)', 'hybrid-GGA'),
    ('ωB97M-V (explicit)', 'hybrid-meta-GGA'),
    # -------- a few “code nicknames” ------
    ('PBE0 (alias PBEh)', 'hybrid-GGA'),
    ('HSE (generic)', 'hybrid-GGA'),
    ('B3PW', 'hybrid-GGA'),
]

_WIDELY_USED_XC_LABEL_CASES = [
    ('PBE', {'XC_GGA_X_PBE', 'XC_GGA_C_PBE'}, 'GGA'),
    ('PBEsol', {'XC_GGA_X_PBE_SOL', 'XC_GGA_C_PBE_SOL'}, 'GGA'),
    ('BLYP', {'XC_GGA_X_B88', 'XC_GGA_C_LYP'}, 'GGA'),
    ('BP86', {'XC_GGA_X_B88', 'XC_GGA_C_P86'}, 'GGA'),
    ('LDA', {'XC_LDA_X', 'XC_LDA_C_PW'}, 'LDA'),
    ('SVWN', {'XC_LDA_X', 'XC_LDA_C_VWN'}, 'LDA'),
    ('PBE0', {'XC_HYB_GGA_XC_PBEH'}, 'hybrid-GGA'),
    ('B3LYP', {'XC_HYB_GGA_XC_B3LYP'}, 'hybrid-GGA'),
    ('HSE06', {'XC_HYB_GGA_XC_HSE06'}, 'hybrid-GGA'),
    ('CAM-B3LYP', {'XC_HYB_GGA_XC_CAM_B3LYP'}, 'hybrid-GGA'),
    ('TPSS', {'XC_MGGA_X_TPSS', 'XC_MGGA_C_TPSS'}, 'meta-GGA'),
    ('SCAN', {'XC_MGGA_X_SCAN', 'XC_MGGA_C_SCAN'}, 'meta-GGA'),
    ('r2SCAN', {'XC_MGGA_X_R2SCAN', 'XC_MGGA_C_R2SCAN'}, 'meta-GGA'),
    ('M06-L', {'XC_MGGA_X_M06_L', 'XC_MGGA_C_M06_L'}, 'meta-GGA'),
    ('M06-2X', {'XC_HYB_MGGA_X_M06_2X', 'XC_MGGA_C_M06_2X'}, 'hybrid-meta-GGA'),
    ('SCAN0', {'XC_HYB_MGGA_X_SCAN0', 'XC_MGGA_C_SCAN'}, 'hybrid-meta-GGA'),
    ('TPSSH', {'XC_HYB_MGGA_XC_TPSSH'}, 'hybrid-meta-GGA'),
    ('ωB97X-V', {'XC_HYB_GGA_XC_WB97X_V'}, 'hybrid-GGA'),
    ('ωB97M-V', {'XC_HYB_MGGA_XC_WB97M_V'}, 'hybrid-meta-GGA'),
]

_WIDELY_USED_XC_NAMES = {raw for raw, _, _ in _WIDELY_USED_XC_LABEL_CASES}
_BROAD_XC_CASES = [
    (raw, expected_family)
    for raw, expected_family in _COMMON_XC_CASES
    if raw not in _WIDELY_USED_XC_NAMES
]


@pytest.mark.parametrize('raw, expected_family', _BROAD_XC_CASES)
def test_dft_expands_broad_functional_set(raw, expected_family):
    dft = DFT()
    dft.xc = XCFunctional(functional_key=raw)
    dft.normalize(EntryArchive(), logger=logger)

    assert dft.xc.components, f'Expansion produced no components for {raw}'
    assert all(c.canonical_label for c in dft.xc.components)
    assert dft.jacobs_ladder == expected_family

    if expected_family.startswith('hybrid'):
        # Schema must not infer α from names
        assert dft.xc.global_exact_exchange is None


@pytest.mark.parametrize('raw', ['SCAN+rVV10', 'r2SCAN + D4', 'B3LYP + D3(BJ)'])
def test_dft_expansion_is_idempotent_for_common_functionals(raw):
    dft = DFT()
    dft.xc = XCFunctional(functional_key=raw)
    dft.normalize(EntryArchive(), logger=logger)
    n1 = len(dft.xc.components or [])
    dft.normalize(EntryArchive(), logger=logger)
    n2 = len(dft.xc.components or [])
    assert n2 == n1


@pytest.mark.parametrize(
    'raw, expected_labels, expected_family', _WIDELY_USED_XC_LABEL_CASES
)
def test_dft_expands_widely_used_functionals_to_expected_labels(
    raw, expected_labels, expected_family
):
    dft = DFT()
    dft.xc = XCFunctional(functional_key=raw)
    dft.normalize(EntryArchive(), logger=logger)

    labels = {c.canonical_label for c in (dft.xc.components or [])}
    assert labels == expected_labels
    assert dft.jacobs_ladder == expected_family
    if expected_family.startswith('hybrid'):
        # Schema must not infer α from names
        assert dft.xc.global_exact_exchange is None
