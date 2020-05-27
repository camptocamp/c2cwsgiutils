def test_ok(app_connection):
    assert app_connection.get_json("ping") == {"pong": True}
