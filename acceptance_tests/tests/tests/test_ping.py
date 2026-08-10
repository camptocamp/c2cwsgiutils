# Copyright (c) 2026, Camptocamp SA


def test_ok(app_connection):
    assert app_connection.get_json("ping") == {"pong": True}
