import os

import pytest
from nomad import infrastructure
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext
from nomad.utils import create_uuid, get_logger
from nomad.utils.exampledata import ExampleData
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.general import Simulation


@pytest.fixture(scope='session', autouse=True)
def logger() -> BoundLogger:
    return get_logger(__name__)


@pytest.fixture(autouse=True)
def archive() -> EntryArchive:
    return EntryArchive(data=Simulation())


@pytest.fixture(scope='session')
def upload_id():
    return 'test_upload'


@pytest.fixture(scope='session')
def main_author():
    from nomad.config import config  # noqa

    return infrastructure.user_management.get_user(username=config.client.user)


@pytest.fixture(scope='session')
def auth():
    from nomad.client import Auth  # noqa
    from nomad.config import config  # noqa

    return Auth(user=config.client.user, password=config.client.password, from_api=True)


@pytest.fixture(scope='session')
def upload_files():
    return {
        'tests/workflow/data/single_point.json': 'parsers/archive',
        'tests/workflow/data/dft.json': 'parsers/archive',
    }


@pytest.fixture(scope='session')
def upload_data(upload_id, main_author, upload_files):
    infrastructure.setup_mongo()
    infrastructure.setup_elastic()

    data = ExampleData(main_author=main_author)
    data.create_upload(upload_id=upload_id)
    for mainfile, parser in upload_files.items():
        _ = data.create_entry_from_file(
            mainfile=mainfile,
            upload_id=upload_id,
            parser_name=parser,
            entry_id=f'test_entry_{os.path.basename(mainfile).split(".")[0]}',
        )
    data.save()
    return data


@pytest.fixture(scope='session')
def context(upload_data, upload_id, main_author):
    from nomad.app.v1.routers.uploads import get_upload_with_read_access  # noqa

    upload = get_upload_with_read_access(upload_id, main_author)
    return ServerContext(upload)
