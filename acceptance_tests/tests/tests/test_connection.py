def test_empty_put_response(app_connection):
    assert app_connection.put_json("empty", expected_status=204) is None


def test_empty_patch_response(app_connection):
    assert app_connection.patch_json("empty", expected_status=204) is None
