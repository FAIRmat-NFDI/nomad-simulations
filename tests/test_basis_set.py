from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import pint

import json

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
    BasisSetContainer,
    EffectiveCorePotential,
    MuffinTinRegion,
    PlaneWaveBasisSet,
    generate_apw,
)
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_method import BaseModelMethod, ModelMethod
from nomad_simulations.schema_packages.model_system import AtomicCell, ModelSystem
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
def test_mt_r_min(mts: list[Optional[MuffinTinRegion]], ref_mt_r_min: float) -> None:
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
    ref_index: int, species_def: dict[str, dict[str, Any]], cutoff: Optional[float]
) -> None:
    """Test the composite structure of APW basis sets."""
    entry = EntryArchive(
        data=Simulation(
            model_system=[
                ModelSystem(
                    cell=[AtomicCell()],
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
def test_apw_base_orbital(ref_n_terms: Optional[int], e: list[float], d_o: list[int]):
    orb = APWBaseOrbital(energy_parameter=e, differential_order=d_o)
    assert orb.get_n_terms() == ref_n_terms


@pytest.mark.parametrize('n_terms, ref_n_terms', [(None, 1), (1, 1), (2, None)])
def test_apw_base_orbital_normalize(
    n_terms: Optional[int], ref_n_terms: Optional[int]
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
def test_apw_orbital(ref_type: Optional[str], do: Optional[int]) -> None:
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
    ref_n_terms: Optional[int],
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
    cutoff: Optional[float],
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


@pytest.mark.parametrize(
    'ftype, n_prim, coeffs_flat',
    [
        ('s', 3, [0.1543, 0.5353, 0.4446]),
        ('sp', 3, [0.1543, 0.5353, 0.4446, -0.0999, 0.3995, 0.7001]),
    ],
)
def test_acf_flat_storage_and_views(ftype, n_prim, coeffs_flat):
    acf = AtomCenteredFunction(
        function_type=ftype,
        n_primitive=n_prim,
        exponents=list(np.linspace(130.7, 6.44, n_prim)),
        contraction_coefficients=coeffs_flat,
    )
    acf.normalize(None, logger)

    # stored flat
    assert acf.contraction_coefficients.shape == (len(coeffs_flat),)

    # matrix view OK
    n_comp = len(ftype) if ftype else 1
    assert acf.coeff_matrix.shape == (n_comp, n_prim)

    # coefficient_sets gives each row
    for i, ltr in enumerate(list(ftype) if ftype else ['s']):
        assert np.allclose(acf.coefficient_sets[ltr], acf.coeff_matrix[i])


def test_atom_centered_basis_set_roundtrip():
    acf = AtomCenteredFunction(
        function_type='s',
        n_primitive=1,
        exponents=[1.0],
        contraction_coefficients=[1.0],
    )
    basis = AtomCenteredBasisSet(functional_composition=[acf])
    d = basis.m_to_dict()
    # functional_composition now serialises as list of reference paths
    # until the archive is fully normalised – just check we round‑trip
    assert 'functional_composition' in d


def test_ao_ordering_default() -> None:
    """
    When nothing is specified, an AtomCenteredBasisSet must default to the
    'Gaussian' ordering convention.
    """
    basis = AtomCenteredBasisSet()
    assert basis.ao_ordering_convention == 'Gaussian'
    # custom order should be absent / None
    assert basis.ao_custom_order is None


def test_ao_ordering_custom() -> None:
    custom_dict = {1: ['pz', 'px', 'py'], 2: ['d0', 'd+1', 'd-1', 'd+2', 'd-2']}
    basis = AtomCenteredBasisSet(
        ao_ordering_convention='Custom',
        ao_custom_order=json.dumps(custom_dict),  # store as JSON string
    )

    d = basis.m_to_dict()
    assert d['ao_ordering_convention'] == 'Custom'
    # round‑trip
    assert json.loads(d['ao_custom_order']) == {
        str(k): v for k, v in custom_dict.items()
    }


@pytest.mark.parametrize(
    'n_terms, am, r_exp, g_exp, coeffs, expect_error',
    [
        (1, [0], [2], [0.5], [-1.23], False),
        (2, [0, 1], [0, 2], [0.1, 0.2], [1.0, -2.0], False),
        (2, [0], [0, 2], [0.1, 0.2], [1.0, -2.0], True),  # am too short
        (1, [0], [0], [0.1], [1.0, 2.0], True),  # coeffs too long
    ],
)
def test_ecp_shape_and_naming(n_terms, am, r_exp, g_exp, coeffs, expect_error):
    at = AtomsState(chemical_symbol='Xe')
    ecp = EffectiveCorePotential(
        species_scope=[at],
        n_core_electrons=54,
        n_terms=n_terms,
        angular_momentum=am,
        r_exponents=r_exp,
        gaussian_exponents=g_exp,
        coefficients=coeffs,
    )
    if expect_error:
        with pytest.raises(ValueError):
            ecp.normalize(None, logger)
    else:
        ecp.normalize(None, logger)
        # name must be derived from species_scope
        assert ecp.name == 'ECP-Xe'
        # integer fields
        assert ecp.n_core_electrons == 54
        assert ecp.n_terms == n_terms
        assert list(ecp.angular_momentum) == am
        assert list(ecp.r_exponents) == r_exp
        # compare gaussian_exponents by magnitude in the defined unit
        mags = np.array(ecp.gaussian_exponents.magnitude)
        assert mags == pytest.approx(np.array(g_exp))
        # coefficients are unitless floats
        assert list(ecp.coefficients) == pytest.approx(coeffs)


def test_ecp_in_atom_centered_basis_set():
    """
    An AtomCenteredBasisSet can carry an ECP in its `ecps` SubSection.
    We assert the `ecps` key appears and the dict has the correct parameters.
    """
    at_H = AtomsState(chemical_symbol='H')

    # build and normalize ECP
    ecp = EffectiveCorePotential(
        species_scope=[at_H],
        n_core_electrons=0,
        n_terms=1,
        angular_momentum=[0],
        r_exponents=[0],
        gaussian_exponents=[0.1],
        coefficients=[-0.5],
    )
    ecp.normalize(None, logger)

    # build and normalize one simple shell
    acf = AtomCenteredFunction(
        function_type='s',
        n_primitive=1,
        exponents=[1.0],
        contraction_coefficients=[1.0],
    )
    acf.normalize(None, logger)

    basis = AtomCenteredBasisSet(
        functional_composition=[acf],
        ecps=[ecp],
    )
    d = basis.m_to_dict()

    # ecps must be a list with one dict
    assert 'ecps' in d and isinstance(d['ecps'], list) and len(d['ecps']) == 1
    ecp_dict = d['ecps'][0]
    assert isinstance(ecp_dict, dict)

    # Check that all ECP parameter fields are present and correct
    expected_keys = {
        'n_core_electrons',
        'n_terms',
        'angular_momentum',
        'r_exponents',
        'gaussian_exponents',
        'coefficients',
    }
    assert expected_keys.issubset(set(ecp_dict.keys()))

    assert ecp_dict['n_core_electrons'] == 0
    assert ecp_dict['n_terms'] == 1
    assert ecp_dict['angular_momentum'] == [0]
    assert ecp_dict['r_exponents'] == [0]
    assert pytest.approx(ecp_dict['gaussian_exponents']) == [0.1]
    assert pytest.approx(ecp_dict['coefficients']) == [-0.5]

    # And the orbital shell remains
    assert 'functional_composition' in d and len(d['functional_composition']) == 1
