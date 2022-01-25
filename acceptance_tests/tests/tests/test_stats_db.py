import subprocess

import pytest


def test_no_extra(app_connection, composition):
    composition.run(
        "run_test",
        "c2cwsgiutils-stats-db",
        "--db=postgresql://www-data:www-data@db:5432/test",
        "--schema=public",
    )


def test_with_extra(app_connection, composition):
    composition.run(
        "run_test",
        "c2cwsgiutils-stats-db",
        "--db=postgresql://www-data:www-data@db:5432/test",
        "--schema=public",
        "--extra=select 'toto', 42",
    )


def test_error(app_connection, composition):
    with pytest.raises(subprocess.CalledProcessError):
        composition.run(
            "run_test",
            "c2cwsgiutils-stats-db",
            "--db=postgresql://www-data:www-data@db:5432/test",
            "--schema=public",
            "--extra=select 'toto, 42",
        )
