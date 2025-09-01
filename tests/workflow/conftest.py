import pytest
from nomad.datamodel import EntryArchive
from nomad.utils import get_logger
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.general import Simulation


@pytest.fixture(scope='session', autouse=True)
def logger() -> BoundLogger:
    return get_logger(__name__)


@pytest.fixture(autouse=True)
def archive() -> EntryArchive:
    return EntryArchive(data=Simulation())
