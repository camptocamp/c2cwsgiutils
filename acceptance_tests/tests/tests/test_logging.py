import logging

_LOG = logging.getLogger(__name__)


def _query(app_connection, params, expected=None):
    all_params = {"secret": "changeme"}
    all_params.update(params)
    response = app_connection.get_json("c2c/logging/level", params=all_params, cors=False)

    all_expected = {"status": 200}
    if "name" in all_params:
        all_expected["name"] = all_params["name"]
    all_expected.update(expected)
    assert response == all_expected


def test_api(app_connection):
    _query(app_connection, {"name": "sqlalchemy.engine"}, {"level": "DEBUG", "effective_level": "DEBUG"})
    _query(app_connection, {"name": "sqlalchemy.engine.sub"}, {"level": "NOTSET", "effective_level": "DEBUG"})

    _query(
        app_connection,
        {"name": "sqlalchemy.engine", "level": "INFO"},
        {"level": "INFO", "effective_level": "INFO"},
    )

    _query(app_connection, {"name": "sqlalchemy.engine"}, {"level": "INFO", "effective_level": "INFO"})
    _query(app_connection, {"name": "sqlalchemy.engine.sub"}, {"level": "NOTSET", "effective_level": "INFO"})

    _query(
        app_connection,
        {"name": "sqlalchemy.engine", "level": "DEBUG"},
        {"level": "DEBUG", "effective_level": "DEBUG"},
    )

    _query(app_connection, {}, {"overrides": {"sqlalchemy.engine": "DEBUG"}})


def test_api_bad_secret(app_connection):
    app_connection.get_json(
        "c2c/logging/level",
        params={"secret": "wrong", "name": "sqlalchemy.engine"},
        expected_status=403,
        cors=False,
    )


def test_api_missing_secret(app_connection):
    app_connection.get_json(
        "c2c/logging/level", params={"name": "sqlalchemy.engine"}, expected_status=403, cors=False
    )
