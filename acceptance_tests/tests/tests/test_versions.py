def test_ok(app_connection):
    params = {"secret": "changeme"}
    response = app_connection.get_json("c2c/versions.json", params=params, cors=False)
    assert "main" in response
    assert "git_hash" in response["main"]
    assert "packages" in response
    assert "pyramid" in response["packages"]
