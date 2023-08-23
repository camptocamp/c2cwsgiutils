import logging
import subprocess  # nosec
from typing import Any, cast

import pytest

from c2cwsgiutils.acceptance import utils
from c2cwsgiutils.acceptance.connection import Connection

_BASE_URL = "http://localhost:8480/api/"
_BASE_URL_APP2 = "http://localhost:8482/api/"
_PROMETHEUS_TEST_URL = "http://localhost:9098/"
_PROMETHEUS_STATS_DB_URL = "http://localhost:9099/"
_LOG = logging.getLogger(__name__)


import os


class Composition:
    """The Docker composition."""

    def __init__(self, cwd: str) -> None:
        self.cwd = os.path.join(os.getcwd(), cwd)
        self.cwd = cwd

    def dc(self, args: list[str], **kwargs: Any) -> str:
        return cast(
            str,
            subprocess.run(  # nosec
                ["docker-compose", *args],
                **{
                    "cwd": self.cwd,
                    "stderr": subprocess.STDOUT,
                    "stdout": subprocess.PIPE,
                    "encoding": "utf-8",
                    "check": True,
                    **kwargs,
                },
            ).stdout,
        )

    def dc_process(self, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # type: ignore[no-any-return, call-overload] # pylint: disable=subprocess-run-check # noqa
            ["docker-compose", *args],
            **{
                "encoding": "utf-8",
                "cwd": self.cwd,
                **kwargs,
            },
        )  # nosec

    def exec(self, container: str, *command: str, **kwargs: dict[str, Any]) -> str:
        return self.dc(["exec", "-T", container] + list(command), **kwargs)

    def exec_proc(
        self, container: str, *command: str, **kwargs: dict[str, Any]
    ) -> subprocess.CompletedProcess[str]:
        return self.dc_process(
            ["exec", "-T", container] + list(command),
            **kwargs,
        )


@pytest.fixture(scope="session")
def composition():
    """
    Fixture that start/stop the Docker composition used for all the tests.
    """
    result = Composition("../tests")
    utils.wait_url(_BASE_URL + "ping")
    return result


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

    return Connection(base_url=_BASE_URL_APP2, origin="http://example.com/")


@pytest.fixture
def prometheus_test_connection(composition):
    """
    Fixture that returns a connection to a running batch container.
    """

    for line in composition.exec("run_test", "ps", "x").split("\n"):
        if "/usr/local/bin/c2cwsgiutils-stats-db" in line.split():
            print("Killing", line.strip().split()[0])
            composition.exec("run_test", "kill", line.strip().split()[0])

    yield Connection(base_url=_PROMETHEUS_TEST_URL, origin="http://example.com/")

    for line in composition.exec("run_test", "ps", "x").split("\n"):
        if "/usr/local/bin/c2cwsgiutils-stats-db" in line.split():
            print("Killing", line.strip().split()[0])
            composition.exec("run_test", "kill", line.strip().split()[0])


@pytest.fixture
def prometheus_stats_db_connection(composition):
    """
    Fixture that returns a connection to a running batch container.
    """
    return Connection(base_url=_PROMETHEUS_STATS_DB_URL, origin="http://example.com/")
