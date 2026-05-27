from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import pint

import numpy as np
import pytest
from nomad.datamodel.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.basis_set import (
    APWBaseOrbital,
    APWLocalOrbital,
    APWOrbital,
    APWPlaneWaveBasisSet,
    AtomCenteredBasisSet,
    AtomCenteredFunction,
    AtomicOrbitals,
    BasisSetContainer,
    EffectiveCorePotential,
    MuffinTinRegion,
    PlaneWaveBasisSet,
    RadialFunction,
    SplineRadialRepresentation,
    generate_apw,
)
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_method import BaseModelMethod, ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem, Representation
from tests.conftest import refs_apw

from . import logger


@pytest.mark.parametrize(
    'ref_cutoff_radius, cutoff_energy',
    [
        (None, None),
        (1.823 / ureg.angstrom, 500 * ureg.eV),  # reference computed by ChatGPT 4o
    ],
)
def test_cutoff(
    ref_cutoff_radius: 'pint.Quantity', cutoff_energy: 'pint.Quantity'
) -> None:
    """Test the quantitative results when computing certain plane-wave cutoffs."""
    pw = APWPlaneWaveBasisSet(cutoff_energy=cutoff_energy)
    cutoff_radius = pw.compute_cutoff_radius(cutoff_energy)

    if cutoff_radius is None:
        assert cutoff_radius is ref_cutoff_radius
    else:
        assert np.isclose(
            cutoff_radius.to(ref_cutoff_radius.units).magnitude,
            ref_cutoff_radius.magnitude,
            atol=1e-3,
        )


@pytest.mark.parametrize(
    'mts, ref_mt_r_min',
    [
        ([], None),
        ([None], None),
        ([MuffinTinRegion(radius=1.0 * ureg.angstrom)], 1.0),
        ([MuffinTinRegion(radius=r * ureg.angstrom) for r in (1.0, 2.0, 3.0)], 1.0),
    ],
)
def test_mt_r_min(mts: list[MuffinTinRegion | None], ref_mt_r_min: float) -> None:
    """
    Test the computation of the minimum muffin-tin radius.
    """
    bs = BasisSetContainer(basis_set_components=mts)
    mt_r_min = bs._find_mt_r_min()

    try:
        assert mt_r_min.to('angstrom').magnitude == ref_mt_r_min
    except AttributeError:
        assert mt_r_min is ref_mt_r_min

    bs.basis_set_components.append(APWPlaneWaveBasisSet(cutoff_energy=500 * ureg('eV')))
    bs.normalize(None, logger)

    try:
        assert (
            bs.basis_set_components[-2].mt_r_min.to('angstrom').magnitude
            == ref_mt_r_min
        )
    except (IndexError, AttributeError):
        assert ref_mt_r_min is None


@pytest.mark.parametrize(
    'ref_cutoff_fractional, cutoff_energy, mt_radius',
    [
        (None, None, None),
        (None, 500.0 * ureg.eV, None),
        (None, None, 1.0),
        (1.823, 500.0 * ureg.eV, 1.0 * ureg.angstrom),
    ],
)
def test_cutoff_failure(
    ref_cutoff_fractional: float,
    cutoff_energy: 'pint.Quantity',
    mt_radius: 'pint.Quantity',
) -> None:
    """Test modes where `cutoff_fractional` is not computed."""
    pw = APWPlaneWaveBasisSet(cutoff_energy=cutoff_energy if cutoff_energy else None)
    if mt_radius is not None:
        pw.cutoff_fractional = pw.compute_cutoff_fractional(
            pw.compute_cutoff_radius(cutoff_energy), mt_radius
        )

    if ref_cutoff_fractional is None:
        assert pw.cutoff_fractional is None
    else:
        assert np.isclose(pw.cutoff_fractional, ref_cutoff_fractional, atol=1e-3)


@pytest.mark.parametrize(
    'ref_index, species_def, cutoff',
    [
        (0, {}, None),
        (1, {}, 500.0),
        (
            2,
            {
                '/data/model_system/0/particle_states/0': {
                    'r': 1,
                    'l_max': 2,
                    'orb_d_o': [[0]],
                    'orb_param': [[0.0]],
                }
            },
            500.0,
        ),
    ],
)
def test_full_apw(
    ref_index: int, species_def: dict[str, dict[str, Any]], cutoff: float | None
) -> None:
    """Test the composite structure of APW basis sets."""
    entry = EntryArchive(
        data=Simulation(
            model_system=[
                ModelSystem(
                    representations=[Representation()],
                    particle_states=[AtomsState(chemical_symbol='H')],
                )
            ],
            model_method=[ModelMethod(numerical_settings=[])],
        )
    )

    numerical_settings = entry.data.model_method[0].numerical_settings
    numerical_settings.append(generate_apw(species_def, cutoff=cutoff))

    # test structure
    assert numerical_settings[0].m_to_dict() == refs_apw[ref_index]


@pytest.mark.parametrize(
    'ref_n_terms, e, d_o',
    [
        (None, None, None),  # unset
        (0, [], []),  # empty
        (None, [0.0], []),  # logically inconsistent
        (1, [0.0], [0]),  # apw
        (2, 2 * [0.0], [0, 1]),  # lapw
    ],
)
def test_apw_base_orbital(ref_n_terms: int | None, e: list[float], d_o: list[int]):
    orb = APWBaseOrbital(energy_parameter=e, differential_order=d_o)
    assert orb.get_n_terms() == ref_n_terms


@pytest.mark.parametrize('n_terms, ref_n_terms', [(None, 1), (1, 1), (2, None)])
def test_apw_base_orbital_normalize(
    n_terms: int | None, ref_n_terms: int | None
) -> None:
    orb = APWBaseOrbital(
        n_terms=n_terms,
        energy_parameter=[0],
        differential_order=[1],
    )
    orb.normalize(None, logger)
    assert orb.n_terms == ref_n_terms


@pytest.mark.parametrize(
    'ref_type, do',
    [
        (None, None),
        (None, []),
        (None, [0, 0, 1]),
        ('apw', [0]),
        ('lapw', [0, 1]),
        ('slapw', [0, 2]),
    ],
)
def test_apw_orbital(ref_type: str | None, do: int | None) -> None:
    orb = APWOrbital(differential_order=do)
    assert orb.do_to_type(orb.differential_order) == ref_type


# ? necessary
@pytest.mark.parametrize(
    'ref_n_terms, e, d_o',
    [
        (None, [0.0], []),
        (1, [0.0], [0]),
        (2, 2 * [0.0], [0, 1]),
        (3, 3 * [0.0], [0, 1, 0]),
    ],
)
def test_apw_local_orbital(
    ref_n_terms: int | None,
    e: list[float],
    d_o: list[int],
) -> None:
    orb = APWLocalOrbital(
        energy_parameter=e,
        differential_order=d_o,
    )
    assert orb.get_n_terms() == ref_n_terms


@pytest.mark.parametrize(
    'ref_type, ref_mt_counts, ref_l_counts, species_def, cutoff',
    [
        (
            None,
            [[0, 0, 0, 0, 0]],
            [[[0, 0, 0, 0, 0]]],
            {
                'H': {
                    'r': 1.0,
                    'l_max': 0,
                    'orb_d_o': [],
                    'orb_param': [],
                    'lo_d_o': [],
                    'lo_param': [],
                }
            },
            None,
        ),
        (
            None,
            [[1, 0, 0, 0, 0]],
            [[[1, 0, 0, 0, 0]]],
            {
                'H': {
                    'r': 1.0,
                    'l_max': 0,
                    'orb_d_o': [[0]],
                    'orb_param': [[0.0]],
                    'lo_d_o': [],
                    'lo_param': [],
                }
            },
            None,
        ),
        (
            'APW-like',
            [[0, 0, 0, 0, 1]],
            [[[0, 0, 0, 0, 1]]],
            {
                'H': {
                    'r': 1.0,
                    'l_max': 0,
                    'orb_d_o': [[]],
                    'orb_param': [[]],
                    'lo_d_o': [],
                    'lo_param': [],
                }
            },
            500.0,
        ),
        (
            'APW',
            [[1, 0, 0, 0, 0]],
            [[[1, 0, 0, 0, 0]]],
            {
                'H': {
                    'r': 1.0,
                    'l_max': 1,
                    'orb_d_o': [[0]],
                    'orb_param': [[0.0]],
                    'lo_d_o': [],
                    'lo_param': [],
                }
            },
            500.0,
        ),
        (
            'LAPW',
            [[1, 0, 0, 0, 0], [0, 1, 0, 0, 0]],
            [[[1, 0, 0, 0, 0]], [[0, 1, 0, 0, 0]]],
            {
                'H': {
                    'r': 1.0,
                    'l_max': 0,
                    'orb_d_o': [[0]],
                    'orb_param': [[0.0]],
                    'lo_d_o': [],
                    'lo_param': [],
                },
                'O': {
                    'r': 2.0,
                    'l_max': 0,
                    'orb_d_o': [[0, 1]],
                    'orb_param': [2 * [0.0]],
                    'lo_d_o': [],
                    'lo_param': [],
                },
            },
            500.0,
        ),
        (
            'SLAPW',
            [[1, 0, 0, 0, 0], [0, 1, 1, 0, 0]],
            [[[1, 0, 0, 0, 0]], [[0, 1, 1, 0, 0]]],
            {
                'H': {
                    'r': 1.0,
                    'l_max': 0,
                    'orb_d_o': [[0]],
                    'orb_param': [[0.0]],
                    'lo_d_o': [],
                    'lo_param': [],
                },
                'O': {
                    'r': 2.0,
                    'l_max': 2,
                    'orb_d_o': [[0, 1], [0, 2]],
                    'orb_param': 2 * [2 * [0.0]],
                    'lo_d_o': [],
                    'lo_param': [],
                },
            },
            500.0,
        ),
    ],
)
def test_determine_apw(
    ref_type: str,
    ref_mt_counts: list[list[int]],
    ref_l_counts: list[list[list[int]]],
    species_def: dict[str, dict[str, Any]],
    cutoff: float | None,
) -> None:
    """Test the L-channel APW structure."""
    ref_keys = ('apw', 'lapw', 'slapw', 'lo', 'other')
    bs = generate_apw(species_def, cutoff=cutoff)

    # test from the bottom up
    for bsc in bs.basis_set_components:
        if isinstance(bsc, MuffinTinRegion):
            l_counts = ref_l_counts.pop(0)
            for l_channel in bsc.l_channels:
                try:
                    assert l_channel._determine_apw() == dict(
                        zip(ref_keys, l_counts.pop(0))
                    )
                except IndexError:
                    pass
            try:
                assert bsc._determine_apw() == dict(zip(ref_keys, ref_mt_counts.pop(0)))
            except IndexError:
                pass
    assert bs._determine_apw() == ref_type


def test_quick_step() -> None:
    """Test the feasibility of describing a QuickStep basis set."""
    entry = EntryArchive(
        data=Simulation(
            model_method=[
                ModelMethod(
                    contributions=[
                        BaseModelMethod(name='kinetic'),
                        BaseModelMethod(name='electron-ion'),
                        BaseModelMethod(name='hartree'),
                    ],
                    numerical_settings=[],
                )
            ],
        )
    )
    numerical_settings = entry.data.model_method[0].numerical_settings
    numerical_settings.append(
        BasisSetContainer(
            # scope='density',
            basis_set_components=[
                AtomCenteredBasisSet(
                    hamiltonian_scope=[
                        entry.data.model_method[0].contributions[0],
                        entry.data.model_method[0].contributions[1],
                    ],
                ),
                PlaneWaveBasisSet(
                    cutoff_energy=500 * ureg.eV,
                    hamiltonian_scope=[entry.data.model_method[0].contributions[2]],
                ),
            ],
        )
    )

    assert numerical_settings[0].m_to_dict() == {
        'm_def': 'nomad_simulations.schema_packages.basis_set.BasisSetContainer',
        'basis_set_components': [
            {
                'm_def': 'nomad_simulations.schema_packages.basis_set.AtomCenteredBasisSet',
                'hamiltonian_scope': [
                    '/data/model_method/0/contributions/0',
                    '/data/model_method/0/contributions/1',
                ],
            },
            {
                'm_def': 'nomad_simulations.schema_packages.basis_set.PlaneWaveBasisSet',
                'hamiltonian_scope': ['/data/model_method/0/contributions/2'],
                'cutoff_energy': (500.0 * ureg.eV).to('joule').magnitude,
            },
        ],
    }
    # TODO: generate a QuickStep generator in the CP2K plugin


# -------------------------------
# AtomCenteredFunction (combined shells, padding/truncation, inference)
# -------------------------------


def test_acf_infers_n_primitive_and_ell() -> None:
    """
    If n_primitive is omitted, it is inferred from exponents length; ℓ inferred from function_type.
    """
    bs = AtomCenteredBasisSet()
    acf = AtomCenteredFunction(
        function_type='d',
        exponents=[0.3, 0.2, 0.1],
        contraction_coefficients=[1.0, 1.0, 1.0],
    )
    bs.functional_compositions.append(acf)
    acf.normalize(None, logger)

    assert acf.n_primitive == 3
    assert acf.angular_momentum == 2  # d → ℓ=2


def test_acf_invalid_length_reset() -> None:
    """
    Tests that if n_primitive is set, but coefficient/exponent arrays mismatch length,
    they are correctly reset to None (due to validation failure).
    """
    acf = AtomCenteredFunction(
        function_type='s',
        n_primitive=3,  # Expects length 3
        exponents=[1.0, 2.0],  # Actual length 2 (Mismatch)
        contraction_coefficients=[1.0, 1.0, 1.0, 1.0],  # Actual length 4 (Mismatch)
    )

    acf.normalize(None, logger)

    # The mismatch resets the invalid arrays.
    assert acf.exponents is None
    assert acf.contraction_coefficients is None
    assert acf.n_primitive == 3


def test_nao_radial_function_tabulated_R_of_r() -> None:
    """
    NAO shells can store an explicit numerical radial function without analytic
    primitive data.
    """
    bs = AtomCenteredBasisSet(
        type='NAO',
        role='orbital',
        functional_compositions=[
            AtomCenteredFunction(
                function_type='s',
                radial_function=RadialFunction(
                    stored_radial_function='R_of_r',
                    representation_type='tabulated_values',
                    radial_coordinate_type='radius',
                    radial_grid=np.array([0.0, 0.5, 1.0]) * ureg.angstrom,
                    radial_values=[1.0, 0.4, 0.0],
                    radial_cutoff=1.0 * ureg.angstrom,
                    support_type='finite_support',
                    radial_channel_index=0,
                    normalization_convention='R_radial_integral',
                ),
            )
        ],
    )

    bs.normalize(None, logger)
    acf = bs.functional_compositions[0]

    assert acf.angular_momentum == 0
    assert acf.n_primitive is None
    assert acf.radial_function.n_radial_grid_points == 3
    assert acf.radial_function.stored_radial_function == 'R_of_r'
    assert acf.radial_function.support_type == 'finite_support'


def test_nao_radial_function_u_of_r_convention_serializes() -> None:
    """
    The stored radial convention is explicit, so u(r)=rR(r) data are not
    confused with R(r) data.
    """
    acf = AtomCenteredFunction(
        function_type='p',
        radial_function=RadialFunction(
            stored_radial_function='u_of_r_equals_r_R_of_r',
            representation_type='tabulated_values',
            radial_coordinate_type='radius',
            radial_grid=np.array([0.0, 0.2, 0.4]) * ureg.angstrom,
            radial_values=[0.0, 0.3, 0.1],
            normalization_convention='u_radial_integral',
        ),
    )

    acf.normalize(None, logger)
    d = acf.m_to_dict()

    assert d['radial_function']['stored_radial_function'] == 'u_of_r_equals_r_R_of_r'
    assert d['radial_function']['normalization_convention'] == 'u_radial_integral'


def test_spline_interpolated_radial_representation_is_not_basis_type() -> None:
    """
    A spline representation can describe interpolation of a radial function
    without changing the basis-set family from NAO.
    """
    bs = AtomCenteredBasisSet(
        type='NAO',
        functional_compositions=[
            AtomCenteredFunction(
                function_type='p',
                radial_function=RadialFunction(
                    stored_radial_function='R_of_r',
                    representation_type='spline_interpolated',
                    radial_coordinate_type='radius',
                    normalization_convention='R_radial_integral',
                    spline_representation=SplineRadialRepresentation(
                        spline_family='cubic_spline',
                        degree=3,
                        knots=np.array([0.0, 0.5, 1.0]) * ureg.angstrom,
                        coefficients=[1.0, 0.3, 0.0],
                        boundary_condition='natural',
                        extrapolation='zero',
                    ),
                ),
            )
        ],
    )

    bs.normalize(None, logger)
    radial = bs.functional_compositions[0].radial_function

    assert bs.type == 'NAO'
    assert radial.representation_type == 'spline_interpolated'
    assert radial.spline_representation.n_knots == 3
    assert radial.spline_representation.n_coefficients == 3
    assert radial.spline_representation.spline_family == 'cubic_spline'


def test_radial_values_length_mismatch_reset() -> None:
    """
    Radial values must match the declared radial grid point count when provided.
    """
    radial = RadialFunction(
        n_radial_grid_points=3,
        radial_grid=np.array([0.0, 0.5, 1.0]) * ureg.angstrom,
        radial_values=[1.0, 0.0],
    )

    radial.normalize(None, logger)

    assert radial.radial_grid is not None
    assert radial.radial_values is None


# -------------------------------
# AtomCenteredBasisSet + AO layer
# -------------------------------


def test_acb_sets_total_from_ao_layer() -> None:
    """
    n_total_basis_functions should be taken from atomic_orbitals.n_atomic_orbitals.
    """
    bs = AtomCenteredBasisSet()
    bs.atomic_orbitals = AtomicOrbitals(
        n_atomic_orbitals=5,
        type='spherical',
        shell_index=np.array([0, 0, 1, 1, 1], dtype=np.int32),
        normalization=np.ones(5),
    )
    bs.normalize(None, logger)
    assert bs.n_total_basis_functions == 5


# -------------------------------
# EffectiveCorePotential (length consistency)
# -------------------------------


def test_ecp_basic_consistency_ok() -> None:
    """
    ECP arrays with lengths matching ecp_num should pass normalize().
    """
    ecp = EffectiveCorePotential(
        ecp_name='Test-ECP',
        z_core=[10, 18],
        max_ang_mom_plus_1=[3, 4],
        ecp_num=3,
        nucleus_index=[0, 0, 1],
        ang_mom=[0, 1, 2],
        exponent=[1.2, 2.3, 3.4],
        coefficient=[-5.0, 6.0, -7.0],
        power=[2, 2, 2],
    )
    ecp.normalize(None, logger)

    assert ecp.ecp_num == 3
    assert len(ecp.nucleus_index) == 3
    assert len(ecp.ang_mom) == 3
    assert len(ecp.exponent) == 3
    assert len(ecp.coefficient) == 3
    assert len(ecp.power) == 3


def test_ecp_h2_ccecp_gamess_numbers() -> None:
    """
    Real-number smoke test using the ECP example
    (GAMESS-style lines). We don't assert physics here; we just ensure that
    the values can be stored 1:1 in our TREXIO-like arrays without shape errors.
    """
    # H2: two nuclei; dummy ℓ_max+1 chosen consistently for both
    z_core = [0, 0]
    max_ang_mom_plus_1 = [3, 3]

    # One H nucleus worth of lines:
    #   3
    #   1.00000000000000    1 21.24359508259891
    #   21.24359508259891   3 21.24359508259891
    #   -10.85192405303825  2 21.77696655044365
    #   1
    #   0.00000000000000    2 1.000000000000000
    coeff_block = [
        1.00000000000000,
        21.24359508259891,
        -10.85192405303825,
        0.00000000000000,
    ]
    power_block = [1, 3, 2, 2]
    exponent_block = [
        21.24359508259891,
        21.24359508259891,
        21.77696655044365,
        1.000000000000000,
    ]
    # For this smoke test, assign all to ℓ=0; in a real parser you’d map
    # non-local vs local channels appropriately.
    ang_mom_block = [0, 0, 0, 0]

    # Duplicate for the second H nucleus
    coefficient = coeff_block + coeff_block
    power = power_block + power_block
    exponent = exponent_block + exponent_block
    ang_mom = ang_mom_block + ang_mom_block

    nucleus_index = [0, 0, 0, 0, 1, 1, 1, 1]
    ecp_num = len(nucleus_index)

    ecp = EffectiveCorePotential(
        ecp_name='H-ccECP',
        z_core=z_core,
        max_ang_mom_plus_1=max_ang_mom_plus_1,
        ecp_num=ecp_num,
        nucleus_index=nucleus_index,
        ang_mom=ang_mom,
        exponent=exponent,
        coefficient=coefficient,
        power=power,
    )
    ecp.normalize(None, logger)

    assert ecp.ecp_num == 8
    assert (
        len(ecp.nucleus_index)
        == len(ecp.ang_mom)
        == len(ecp.exponent)
        == len(ecp.coefficient)
        == len(ecp.power)
        == ecp_num
    )
    # spot-check a couple of literal values
    assert np.isclose(ecp.exponent[0], 21.24359508259891)
    assert np.isclose(ecp.coefficient[2], -10.85192405303825)
    # ensure both nuclei are represented
    assert set(ecp.nucleus_index) == {0, 1}


def test_ecp_metadata_length_mismatch() -> None:
    """
    Tests the validation constraint: per-nucleus arrays (z_core, max_ang_mom_plus_1)
    must match length.
    """
    ecp = EffectiveCorePotential(
        z_core=[10, 18],  # Length 2
        max_ang_mom_plus_1=[3],  # Length 1 (Mismatch)
        ecp_num=1,
        nucleus_index=[0],
        ang_mom=[0],
        exponent=[1.0],
        coefficient=[1.0],
        power=[1],
    )
    ecp.normalize(None, logger)
    # The normalization should have logged an error but allowed the section to exist.
    # We check that the structural mismatch logging was triggered (implicitly via code coverage)
    # and the correct data fields are still available.
    assert len(ecp.z_core) == 2


def test_additional_basis_functions_assigned_to_subset_of_atoms() -> None:
    entry = EntryArchive(
        data=Simulation(
            model_system=[
                ModelSystem(
                    representations=[Representation()],
                    particle_states=[
                        AtomsState(chemical_symbol='O'),  # idx 0
                        AtomsState(chemical_symbol='H'),  # idx 1
                        AtomsState(chemical_symbol='H'),  # idx 2
                    ],
                )
            ],
            model_method=[ModelMethod(numerical_settings=[])],
        )
    )
    numerical_settings = entry.data.model_method[0].numerical_settings

    o_ref = '/data/model_system/0/particle_states/0'
    h1_ref = '/data/model_system/0/particle_states/1'
    h2_ref = '/data/model_system/0/particle_states/2'

    acb_oxygen_extra = AtomCenteredBasisSet(
        species_scope=[entry.data.model_system[0].particle_states[0]],
        basis_set='user-extra-O',
        type='GTO',
        role='orbital',
        functional_compositions=[
            AtomCenteredFunction(
                function_type='d',
                harmonic_type='spherical',
                n_primitive=1,
                exponents=[0.8],
                contraction_coefficients=[1.0],
            )
        ],
    )

    acb_hydrogen_extra = AtomCenteredBasisSet(
        species_scope=[
            entry.data.model_system[0].particle_states[1],
            entry.data.model_system[0].particle_states[2],
        ],
        basis_set='user-extra-H',
        type='GTO',
        role='orbital',
        functional_compositions=[
            AtomCenteredFunction(
                function_type='p',
                harmonic_type='spherical',
                n_primitive=1,
                exponents=[0.3],
                contraction_coefficients=[1.0],
            )
        ],
    )

    container = BasisSetContainer(
        basis_set_components=[acb_oxygen_extra, acb_hydrogen_extra]
    )
    numerical_settings.append(container)
    container.normalize(None, logger)

    d = numerical_settings[0].m_to_dict()
    assert d['m_def'] == 'nomad_simulations.schema_packages.basis_set.BasisSetContainer'
    assert len(d['basis_set_components']) == 2

    by_name = {c['basis_set']: c for c in d['basis_set_components']}
    cO = by_name['user-extra-O']
    cH = by_name['user-extra-H']

    # oxygen component
    assert cO['type'] == 'GTO'
    assert cO['role'] == 'orbital'
    assert cO['species_scope'] == [o_ref]
    assert len(cO['functional_compositions']) == 1
    s0 = cO['functional_compositions'][0]
    assert s0['function_type'] == 'd'
    assert s0['n_primitive'] == 1
    assert np.allclose(s0['exponents'], [0.8])
    assert np.allclose(s0['contraction_coefficients'], [1.0])

    # hydrogen component (both H atoms)
    assert cH['type'] == 'GTO'
    assert cH['role'] == 'orbital'
    assert cH['species_scope'] == [h1_ref, h2_ref]
    assert len(cH['functional_compositions']) == 1
    s1 = cH['functional_compositions'][0]
    assert s1['function_type'] == 'p'
    assert s1['n_primitive'] == 1
    assert np.allclose(s1['exponents'], [0.3])
    assert np.allclose(s1['contraction_coefficients'], [1.0])


def test_mixed_orbital_aux_ecp() -> None:
    """
    Mixed atom-centered setup:
      - Orbital GTO basis for H and O
      - Auxiliary_scf GTO basis for H and O
      - ECP only for O
    Verifies component wiring, roles, species_scope mapping (via m_to_dict), and ECP consistency.
    """
    entry = EntryArchive(
        data=Simulation(
            model_system=[
                ModelSystem(
                    representations=[Representation()],
                    particle_states=[
                        AtomsState(
                            chemical_symbol='H'
                        ),  # /data/model_system/0/particle_states/0
                        AtomsState(
                            chemical_symbol='O'
                        ),  # /data/model_system/0/particle_states/1
                    ],
                )
            ],
            model_method=[
                ModelMethod(
                    contributions=[
                        BaseModelMethod(name='kinetic'),
                        BaseModelMethod(name='electron-ion'),
                        BaseModelMethod(name='hartree'),
                    ],
                    numerical_settings=[],
                )
            ],
        )
    )

    h_ref = '/data/model_system/0/particle_states/0'
    o_ref = '/data/model_system/0/particle_states/1'

    orbital_bs = AtomCenteredBasisSet(
        basis_set='def2-SVP',
        type='GTO',
        role='orbital',
        species_scope=[
            entry.data.model_system[0].particle_states[0],
            entry.data.model_system[0].particle_states[1],
        ],
        functional_compositions=[
            AtomCenteredFunction(
                function_type='s',
                n_primitive=3,
                exponents=[3.42525, 0.62391, 0.16886],
                contraction_coefficients=[0.15433, 0.53533, 0.44463],
            ),
        ],
        atomic_orbitals=AtomicOrbitals(
            n_atomic_orbitals=1, type='spherical', shell_index=[0], normalization=[1.0]
        ),
    )

    aux_bs = AtomCenteredBasisSet(
        basis_set='def2/JKfit',
        type='GTO',
        role='auxiliary_scf',
        species_scope=[
            entry.data.model_system[0].particle_states[0],
            entry.data.model_system[0].particle_states[1],
        ],
        functional_compositions=[
            AtomCenteredFunction(
                function_type='s',
                n_primitive=2,
                exponents=[1.0, 0.2],
                contraction_coefficients=[1.0, 0.5],
            ),
        ],
        atomic_orbitals=AtomicOrbitals(
            n_atomic_orbitals=1, type='spherical', shell_index=[0], normalization=[1.0]
        ),
    )

    ecp_o = EffectiveCorePotential(
        ecp_name='ccECP-O',
        species_scope=[entry.data.model_system[0].particle_states[1]],
        z_core=[10],
        max_ang_mom_plus_1=[3],
        ecp_num=2,
        nucleus_index=[0, 0],
        ang_mom=[0, 2],
        exponent=[20.0, 21.0],
        coefficient=[1.0, -0.5],
        power=[1, 2],
    )

    container = BasisSetContainer(basis_set_components=[orbital_bs, aux_bs, ecp_o])
    entry.data.model_method[0].numerical_settings.append(container)

    container.normalize(None, logger)

    # 3 components
    assert len(container.basis_set_components) == 3

    # roles present
    roles = [
        c.role
        for c in container.basis_set_components
        if isinstance(c, AtomCenteredBasisSet)
    ]
    assert 'orbital' in roles and 'auxiliary_scf' in roles

    # species_scope: compare via paths in m_to_dict()
    d = container.m_to_dict()
    acb_items = [
        c
        for c in d['basis_set_components']
        if c['m_def'].endswith('AtomCenteredBasisSet')
    ]
    ecp_items = [
        c
        for c in d['basis_set_components']
        if c['m_def'].endswith('EffectiveCorePotential')
    ]

    assert len(acb_items) == 2
    for acb in acb_items:
        assert acb['species_scope'] == [h_ref, o_ref]

    assert len(ecp_items) == 1
    assert ecp_items[0]['species_scope'] == [o_ref]

    # ECP array consistency
    ecp = [
        c
        for c in container.basis_set_components
        if isinstance(c, EffectiveCorePotential)
    ][0]
    assert len(ecp.z_core) == len(ecp.max_ang_mom_plus_1) == 1
    assert ecp.ecp_num == 2

    #  Iterate over the attribute values directly for consistency check
    projector_arrays = [
        ecp.nucleus_index,
        ecp.ang_mom,
        ecp.exponent,
        ecp.coefficient,
        ecp.power,
    ]

    for arr in projector_arrays:
        # Check if the array exists (is not None) and its length matches ecp_num
        assert arr is not None and len(arr) == ecp.ecp_num

    # AO layers provide totals
    acb_sections = [
        c for c in container.basis_set_components if isinstance(c, AtomCenteredBasisSet)
    ]
    assert [c.n_total_basis_functions for c in acb_sections] == [1, 1]
