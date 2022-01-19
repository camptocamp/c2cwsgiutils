import logging

import psycopg2
import pytest

from c2cwsgiutils.acceptance import utils
from c2cwsgiutils.acceptance.composition import Composition
from c2cwsgiutils.acceptance.connection import Connection

BASE_URL = "http://" + utils.DOCKER_GATEWAY + ":8480/api/"
LOG = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def composition(request):
    """
    Fixture that start/stop the Docker composition used for all the tests.
    """
    result = Composition(
        request,
        "/acceptance_tests/docker-compose.yaml",
        coverage_paths=["c2cwsgiutils_app_1:/tmp/coverage"],
    )
    utils.wait_url(BASE_URL + "ping")
    return result


@pytest.fixture
def app_connection(composition):
    """
    Fixture that returns a connection to a running batch container.
    """
    return Connection(base_url=BASE_URL, origin="http://example.com/")


@pytest.fixture(scope="session")
def master_db_setup(composition):
    return _create_table(composition, master=True)


@pytest.fixture(scope="session")
def slave_db_setup(composition):
    return _create_table(composition, master=False)


def _create_table(composition, master):
    name = "master" if master else "slave"
    composition.run("alembic_" + name, "/app/run_alembic.sh")
    connection = _connect(master)
    with connection.cursor() as curs:
        LOG.info("Creating data for " + name)
        curs.execute("INSERT INTO hello (value) VALUES (%s)", (name,))
    connection.commit()
    return connection


def _connect(master):
    return utils.retry_timeout(
        lambda: psycopg2.connect(
            database="test",
            user="www-data",
            password="www-data",
            host=utils.DOCKER_GATEWAY,
            port=15432 if master else 25432,
        )
    )


@pytest.fixture
def master_db_connection(master_db_setup):
    return master_db_setup


@pytest.fixture
def slave_db_connection(slave_db_setup):
    return master_db_setup
