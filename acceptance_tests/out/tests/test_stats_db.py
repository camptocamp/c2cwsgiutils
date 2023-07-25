import logging
import subprocess
import threading
import time

import pytest

_LOG = logging.getLogger(__name__)


class _PrometheusThread:
    def __init__(self, connection, prometheus):
        self._connection = connection
        self._prometheus = prometheus

    def __call__(self):
        while not self._prometheus.stop:
            try:
                with self._connection.session.get(self._connection.base_url) as r:
                    _LOG.debug("Prometheus: %s", r.text)
            except Exception as e:
                _LOG.debug("Prometheus: %s", e)
            time.sleep(2)


class _Prometheus:
    stop = False

    def __init__(self, connection):
        self.thread = threading.Thread(target=_PrometheusThread(connection, self))

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop = True


def test_no_call(app2_connection, prometheus_test_connection, composition):
    with pytest.raises(subprocess.TimeoutExpired):
        composition.exec(
            "run_test",
            "c2cwsgiutils-stats-db",
            "--db=postgresql://www-data:www-data@db:5432/test",
            "--schema=public",
            timeout=30,
        )


def test_no_extra(app2_connection, prometheus_test_connection, composition):
    with _Prometheus(prometheus_test_connection):
        composition.exec(
            "run_test",
            "c2cwsgiutils-stats-db",
            "--db=postgresql://www-data:www-data@db:5432/test",
            "--schema=public",
            timeout=30,
        )


def test_with_extra(app2_connection, prometheus_test_connection, composition):
    with _Prometheus(prometheus_test_connection):
        composition.exec(
            "run_test",
            "c2cwsgiutils-stats-db",
            "--db=postgresql://www-data:www-data@db:5432/test",
            "--schema=public",
            "--extra=select 'toto', 42",
            timeout=30,
        )


def test_with_extra_gauge(app2_connection, prometheus_test_connection, composition):
    with _Prometheus(prometheus_test_connection):
        composition.exec(
            "run_test",
            "c2cwsgiutils-stats-db",
            "--db=postgresql://www-data:www-data@db:5432/test",
            "--schema=public",
            "--extra-gauge",
            "select 'toto', 42",
            "toto",
            "toto help",
            timeout=30,
        )


def test_error(app2_connection, prometheus_test_connection, composition):
    with _Prometheus(prometheus_test_connection):
        with pytest.raises(subprocess.CalledProcessError):
            composition.exec(
                "run_test",
                "c2cwsgiutils-stats-db",
                "--db=postgresql://www-data:www-data@db:5432/test",
                "--schema=public",
                "--extra=select 'toto, 42",
                timeout=30,
            )


def test_standalone(prometheus_stats_db_connection, composition):
    """
    Test that stats db is correctly waiting for the Prometheus call, and exit after the call.
    """
    # To be able to debug
    composition.dc_process(["logs", "stats_db"])
    ps = [l for l in composition.dc(["ps"]).split("\n") if "c2cwsgiutils_stats_db_" in l]
    print("\n".join(ps))
    assert len(ps) == 1
    assert " Up " in ps[0]
    print("Call Prometheus URL")
    prometheus_stats_db_connection.session.get(prometheus_stats_db_connection.base_url)
    ps = [l for l in composition.dc(["ps"]).split("\n") if "c2cwsgiutils_stats_db_" in l]
    print("\n".join(ps))
    assert len(ps) == 1
    assert ps[0].strip().endswith(" Exit 0")
