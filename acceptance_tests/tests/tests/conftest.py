import logging

import psycopg2
import pytest

from c2cwsgiutils.acceptance import utils
from c2cwsgiutils.acceptance.connection import Connection

_BASE_URL = "http://app:8080/api/"
_BASE_URL_APP2 = "http://app2:8080/api/"
_PROMETHEUS_URL = "http://app2:9090/metrics"
_PROMETHEUS_TEST_URL = "http://run_test:9090/metrics"
_PROMETHEUS_STATS_DB_URL = "http://stats_db:9090/metrics"
_LOG = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def composition(request):
    """
    Fixture that start/stop the Docker composition used for all the tests.
    """
    utils.wait_url(_BASE_URL + "ping")
    return None


@pytest.fixture
def app_connection(composition):
    """
    Fixture that returns a connection to a running batch container.
    """

    del composition
    return Connection(base_url=_BASE_URL, origin="http://example.com/")


@pytest.fixture
def app2_connection(composition):
    """
    Fixture that returns a connection to a running batch container.
    """

    del composition
    return Connection(base_url=_BASE_URL_APP2, origin="http://example.com/")


@pytest.fixture
def prometheus_connection(composition):
    """
    Fixture that returns a connection to a running batch container.
    """

    del composition
    return Connection(base_url=_PROMETHEUS_URL, origin="http://example.com/")


@pytest.fixture
def prometheus_test_connection(composition):
    """
    Fixture that returns a connection to a running batch container.
    """

    del composition
    return Connection(base_url=_PROMETHEUS_TEST_URL, origin="http://example.com/")


@pytest.fixture
def prometheus_stats_db_connection(composition):
    """
    Fixture that returns a connection to a running batch container.
    """

    del composition
    return Connection(base_url=_PROMETHEUS_STATS_DB_URL, origin="http://example.com/")


@pytest.fixture(scope="session")
def master_db_setup(composition):
    del composition
    return _create_table(master=True)


@pytest.fixture(scope="session")
def slave_db_setup(composition):
    del composition
    return _create_table(master=False)


def _create_table(master):
    name = "master" if master else "slave"
    connection = _connect(master)
    with connection.cursor() as curs:
        _LOG.info("Creating data for %s", name)
        curs.execute("DELETE FROM hello")
        curs.execute("INSERT INTO hello (value) VALUES (%s)", (name,))
    connection.commit()
    return connection


def _connect(master):
    return utils.retry_timeout(
        lambda: psycopg2.connect(
            database="test",
            user="www-data",
            password="www-data",
            host="db" if master else "db_slave",
            port=5432,
        )
    )


@pytest.fixture
def master_db_connection(master_db_setup):
    return master_db_setup


@pytest.fixture
def slave_db_connection(slave_db_setup):
    return master_db_setup
