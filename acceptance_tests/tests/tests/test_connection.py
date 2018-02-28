def test_empty_response(app_connection):
    assert app_connection.put_json("empty", expected_status=204) is None
