# Copyright (c) 2026, Camptocamp SA


def test_sql(app_connection):
    app_connection.get_json("timeout/sql", expected_status=500)
