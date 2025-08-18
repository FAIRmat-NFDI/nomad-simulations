import logging
from io import StringIO

import pytest
from nomad.utils import get_logger

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
def test_log(func, logger_kwarg, logger_name):
    """
    Test for the `log` decorator.
    """

    stream = StringIO('')
    logger = logger_kwarg if logger_kwarg is not None else LOGGER
    if logger_name == 'nomad_simulations.schema_packages.utils.utils':
        # inject streaming steam handler to the default logger
        from nomad_simulations.schema_packages.utils.utils import (
            DEFAULT_LOGGER as logger,
        )  # noqa

    handler = logging.StreamHandler(stream)
    logger.setLevel(logging.DEBUG)
    # remove prior handlers
    for handler in logger.handlers:
        logger.removeHandler(handler)
    logger.addHandler(handler)

    if logger_kwarg:
        func('a', logger=logger)
    else:
        func('a')

    assert func.__annotations__['logger'].name == logger_name

    stream.seek(0)
    lines = stream.readlines()

    assert 'Executing func' in lines[0]
    assert f'Exception raised in {func.__name__}: invalid literal for int' in lines[1]

    logger.removeHandler(handler)
    handler.close()


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
