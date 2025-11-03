import pytest
import structlog
from nomad.utils import get_logger

from nomad_simulations.schema_packages.model_system import (
    AtomicCell,
    ModelSystem,
    Symmetry,
)
from nomad_simulations.schema_packages.utils import get_sibling_section, log
from nomad_simulations.schema_packages.variables import Energy2 as Energy
from nomad_simulations.schema_packages.variables import Temperature

from . import logger

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
    c0 = AtomicCell(type='original')
    c1 = AtomicCell(type='primitive')
    parent.cell.extend([c0, c1])
    s = Symmetry()
    parent.symmetry.append(s)

    # First call
    got0 = get_sibling_section(s, 'cell', logger, index_sibling=0)
    got1 = get_sibling_section(s, 'cell', logger, index_sibling=1)

    assert got0 is c0
    assert got1 is c1

    # Second call (idempotent return values; we purposefully do NOT assert on logs)
    got0_bis = get_sibling_section(s, 'cell', logger, index_sibling=0)
    got1_bis = get_sibling_section(s, 'cell', logger, index_sibling=1)

    assert got0_bis is c0
    assert got1_bis is c1

    # Structure was not mutated by calls
    assert parent.cell == [c0, c1]
    assert parent.symmetry == [s]


@pytest.mark.parametrize(
    'sibling_section_name, index_sibling, expected',
    [
        ('', 0, None),  # empty name → None
        ('cell', 5, None),  # OOB index → None
    ],
)
def test_get_sibling_section_edge_cases_stable(
    sibling_section_name, index_sibling, expected
):
    parent = ModelSystem()
    cell = AtomicCell(type='original')
    symm = Symmetry()
    parent.cell.append(cell)
    parent.symmetry.append(symm)

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
    assert parent.cell == [cell]
    assert parent.symmetry == [symm]


# ! Missing test for RusselSandersState (but this class will probably be deprecated)
