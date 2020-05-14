import logging

LOG = logging.getLogger(__name__)


def _query(app_connection, params, expected=None):
    all_params = {"secret": "changeme"}
    all_params.update(params)
    response = app_connection.get_json("c2c/db/maintenance", params=all_params, cors=False)

    all_expected = {"status": 200}
    if "readonly" in all_params:
        all_expected["readonly"] = all_params["readonly"] == "true"
    if expected:
        all_expected.update(expected)
    assert response == all_expected


def test_api(app_connection):
    _query(app_connection, {}, {"current_readonly": None})
    _query(app_connection, {"readonly": "false"})
    _query(app_connection, {}, {"current_readonly": False})
    _query(app_connection, {"readonly": "true"})
    _query(app_connection, {}, {"current_readonly": True})


def test_api_bad_secret(app_connection):
    app_connection.get_json(
        "c2c/db/maintenance", params={"secret": "wrong", "readonly": "true"}, expected_status=403, cors=False
    )


def test_api_missing_secret(app_connection):
    app_connection.get_json(
        "c2c/db/maintenance", params={"readonly": "true"}, expected_status=403, cors=False
    )
