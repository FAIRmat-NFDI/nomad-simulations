import logging
from io import StringIO

import pytest
import structlog
from nomad.utils import get_logger
from structlog.testing import LogCapture

from nomad_simulations.schema_packages.model_system import (
    AtomicCell,
    ModelSystem,
    Symmetry,
)
from nomad_simulations.schema_packages.utils import (
    get_sibling_section,
    is_not_representative,
    log,
)
from nomad_simulations.schema_packages.variables import Energy2 as Energy
from nomad_simulations.schema_packages.variables import Temperature

from . import logger

LOGGER = get_logger('TestLogger')


@pytest.fixture
def log_output():
    return LogCapture()


@pytest.fixture(autouse=True)
def fixture_configure_structlog(log_output):
    structlog.configure(processors=[log_output])


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


def test_get_sibling_section():
    """
    Test the `get_sibling_section` utility function.
    """
    parent_section = ModelSystem()
    section = AtomicCell(type='original')
    parent_section.cell.append(section)
    sibling_section = Symmetry()
    parent_section.symmetry.append(sibling_section)
    assert get_sibling_section(section, '', logger) is None
    assert get_sibling_section(section, 'symmetry', logger) == sibling_section
    assert get_sibling_section(sibling_section, 'cell', logger).type == section.type
    assert get_sibling_section(section, 'symmetry', logger, index_sibling=2) is None
    section2 = AtomicCell(type='primitive')
    parent_section.cell.append(section2)
    assert (
        get_sibling_section(sibling_section, 'cell', logger, index_sibling=0).type
        == 'original'
    )
    assert (
        get_sibling_section(sibling_section, 'cell', logger, index_sibling=0).type
        == section.type
    )
    assert (
        get_sibling_section(sibling_section, 'cell', logger, index_sibling=1).type
        == section2.type
    )
    assert (
        get_sibling_section(sibling_section, 'cell', logger, index_sibling=1).type
        == 'primitive'
    )


def test_is_not_representative():
    """
    Test the `is_not_representative` utility function.
    """
    assert is_not_representative(None, logger) is None
    assert is_not_representative(ModelSystem(), logger)
    assert not is_not_representative(ModelSystem(is_representative=True), logger)


# ! Missing test for RusselSandersState (but this class will probably be deprecated)
