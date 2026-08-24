import numpy as np
import pint
import pytest
import structlog
from nomad.utils import get_logger

from nomad_simulations.schema_packages.model_system import (
    ModelSystem,
    Representation,
    Symmetry,
)
from nomad_simulations.schema_packages.utils import (
    get_sibling_section,
    log,
    resolve_frontier_levels,
)

from . import logger

ureg = pint.get_application_registry()

LOGGER = get_logger('TestLogger')


def f_kernel(f, a):
    logger = f.__annotations__['logger']
    logger.info('Executing func.')
    return int(a)


@log(logger=LOGGER)
def example_func1(a):
    return f_kernel(example_func1, a)


@log
def example_func2(a):
    return f_kernel(example_func2, a)


@pytest.mark.skipif(not structlog.is_configured(), reason='Cannot use struclog.')
@pytest.mark.parametrize(
    'func, logger_kwarg, logger_name',
    [
        pytest.param(example_func1, None, 'TestLogger', id='defined'),
        pytest.param(
            example_func2, get_logger('TestLogger2'), 'TestLogger2', id='as_kwarg'
        ),
        pytest.param(
            example_func2,
            None,
            'nomad_simulations.schema_packages.utils.utils',
            id='default',
        ),
    ],
)
def test_log(func, logger_kwarg, logger_name, log_output):
    """
    Test for the `log` decorator.
    """

    logger = logger_kwarg if logger_kwarg is not None else LOGGER
    if logger_kwarg:
        func('a', logger=logger)
    else:
        func('a')

    flogger = func.__annotations__['logger']
    assert (
        flogger.logger.name
        if hasattr(flogger, 'logger')
        else flogger.name == logger_name
    )

    assert 'Executing func' in log_output.entries[0].get('event')
    assert (
        f'Exception raised in {func.__name__}: invalid literal for int'
        in log_output.entries[1].get('event')
    )


def test_get_sibling_section_result_idempotent_and_no_mutation():
    parent = ModelSystem()
    c0 = Representation(name='original')
    c1 = Representation(name='primitive')
    parent.representations.extend([c0, c1])
    s = Symmetry()
    parent.symmetry = s

    # First call
    got0 = get_sibling_section(s, 'representations', logger, index_sibling=0)
    got1 = get_sibling_section(s, 'representations', logger, index_sibling=1)

    assert got0 is c0
    assert got1 is c1

    # Second call (idempotent return values; we purposefully do NOT assert on logs)
    got0_bis = get_sibling_section(s, 'representations', logger, index_sibling=0)
    got1_bis = get_sibling_section(s, 'representations', logger, index_sibling=1)

    assert got0_bis is c0
    assert got1_bis is c1

    # Structure was not mutated by calls
    assert parent.representations == [c0, c1]
    assert parent.symmetry == s


@pytest.mark.parametrize(
    'sibling_section_name, index_sibling, expected',
    [
        ('', 0, None),  # empty name → None
        ('representations', 5, None),  # OOB index → None
    ],
)
def test_get_sibling_section_edge_cases_stable(
    sibling_section_name, index_sibling, expected
):
    parent = ModelSystem()
    representation = Representation(name='original')
    symm = Symmetry()
    parent.representations.append(representation)
    parent.symmetry = symm

    # Call twice; both should yield the same (None here)
    out1 = get_sibling_section(
        symm, sibling_section_name, logger, index_sibling=index_sibling
    )
    out2 = get_sibling_section(
        symm, sibling_section_name, logger, index_sibling=index_sibling
    )

    assert out1 is expected
    assert out2 is expected

    # No mutation of structure
    assert parent.representations == [representation]
    assert parent.symmetry == symm


def test_get_sibling_section_uses_cache():
    """Test that get_sibling_section caches results to avoid repeated XPath lookups."""
    parent = ModelSystem()
    c0 = Representation(name='original')
    c1 = Representation(name='primitive')
    parent.representations.extend([c0, c1])
    s = Symmetry()
    parent.symmetry = s

    # Verify cache is initially empty
    assert '_sibling_representations_0' not in s.m_cache
    assert '_sibling_representations_1' not in s.m_cache

    # First call - should populate cache
    got0 = get_sibling_section(s, 'representations', logger, index_sibling=0)
    assert got0 is c0
    assert '_sibling_representations_0' in s.m_cache
    assert s.m_cache['_sibling_representations_0'] is c0

    # Second call - should use cache
    got0_cached = get_sibling_section(s, 'representations', logger, index_sibling=0)
    assert got0_cached is c0
    assert got0_cached is s.m_cache['_sibling_representations_0']

    # Different index - should create separate cache entry
    got1 = get_sibling_section(s, 'representations', logger, index_sibling=1)
    assert got1 is c1
    assert '_sibling_representations_1' in s.m_cache
    assert s.m_cache['_sibling_representations_1'] is c1


def test_get_sibling_section_caches_none_results():
    """Test that None results (failed lookups) are also cached to avoid repeated failures."""
    parent = ModelSystem()
    representation = Representation(name='original')
    parent.representations.append(representation)
    s = Symmetry()
    parent.symmetry = s

    # Out of bounds lookup - should cache None
    cache_key = '_sibling_representations_5'
    assert cache_key not in s.m_cache

    result1 = get_sibling_section(s, 'representations', logger, index_sibling=5)
    assert result1 is None
    assert cache_key in s.m_cache
    assert s.m_cache[cache_key] is None

    # Second call - should return cached None
    result2 = get_sibling_section(s, 'representations', logger, index_sibling=5)
    assert result2 is None
    assert result2 is s.m_cache[cache_key]


def test_get_sibling_section_cache_key_uniqueness():
    """Test that cache keys are unique per sibling name and index."""
    parent = ModelSystem()
    rep = Representation(name='rep')
    parent.representations.append(rep)
    s = Symmetry()
    parent.symmetry = s

    # Cache different siblings
    get_sibling_section(s, 'representations', logger, index_sibling=0)
    get_sibling_section(s, 'cell', logger, index_sibling=0)

    # Should have separate cache entries
    assert '_sibling_representations_0' in s.m_cache
    assert '_sibling_cell_0' in s.m_cache
    assert s.m_cache['_sibling_representations_0'] is not None
    # cell might be None but key should exist


# ! Missing test for RusselSandersState (but this class will probably be deprecated)


# `resolve_frontier_levels`: pure HOMO/LUMO resolution from level energies and
# occupations. HOMO = highest occupied, LUMO = lowest unoccupied; occupied means
# occupation > tol. Returns (None, None) when the boundary is unresolvable.
@pytest.mark.parametrize(
    'values, occupations, tol, expected',
    [
        # insulator: clean occupied/unoccupied split
        ([-2.0, -1.0, 0.5, 1.5], [2.0, 2.0, 0.0, 0.0], 1e-6, (-1.0, 0.5)),
        # HOMO/LUMO are the extremes of each subset, not necessarily adjacent
        ([1.5, -1.0, -2.0, 0.5], [0.0, 2.0, 2.0, 0.0], 1e-6, (-1.0, 0.5)),
        # all occupied -> no boundary
        ([-2.0, -1.0], [2.0, 2.0], 1e-6, (None, None)),
        # all unoccupied -> no boundary
        ([0.5, 1.5], [0.0, 0.0], 1e-6, (None, None)),
        # length mismatch -> unresolvable
        ([-1.0, 0.5, 1.5], [2.0, 0.0], 1e-6, (None, None)),
        # tolerance boundary: occupation just above tol counts as occupied
        ([-1.0, 0.5], [1e-3, 0.0], 1e-6, (-1.0, 0.5)),
        # tolerance boundary: occupation just below tol counts as unoccupied
        ([-1.0, 0.5], [1e-9, 1e-9], 1e-6, (None, None)),
    ],
)
def test_resolve_frontier_levels(values, occupations, tol, expected):
    vals = np.array(values) * ureg.joule
    occ = np.array(occupations)
    homo, lumo = resolve_frontier_levels(vals, occ, tol)
    e_homo, e_lumo = expected
    if e_homo is None:
        assert homo is None and lumo is None
    else:
        assert homo.magnitude == pytest.approx(e_homo)
        assert lumo.magnitude == pytest.approx(e_lumo)


@pytest.mark.parametrize(
    'values, occupations',
    [(None, np.array([2.0, 0.0])), (np.array([-1.0, 0.5]) * ureg.joule, None)],
)
def test_resolve_frontier_levels_none_inputs(values, occupations):
    assert resolve_frontier_levels(values, occupations, 1e-6) == (None, None)


def test_resolve_frontier_levels_rejects_nan_energy():
    # a NaN energy would propagate into a NaN frontier/gap; treat it as unresolvable
    vals = np.array([-1.0, np.nan, 1.5]) * ureg.joule
    occ = np.array([2.0, 2.0, 0.0])
    assert resolve_frontier_levels(vals, occ, 1e-6) == (None, None)


def test_resolve_frontier_levels_does_not_mutate_inputs():
    vals = np.array([-1.0, 0.5, 1.5]) * ureg.joule
    occ = np.array([2.0, 0.0, 0.0])
    vals_copy, occ_copy = vals.magnitude.copy(), occ.copy()
    resolve_frontier_levels(vals, occ, 1e-6)
    assert np.array_equal(vals.magnitude, vals_copy)
    assert np.array_equal(occ, occ_copy)
