def test_auto_requests(app_connection):
    result = app_connection.get_json("tracking/1")
    assert result["request_id"] == result["sub"]["request_id"]


def test_manual_requests(app_connection):
    result = app_connection.get_json("tracking/1", headers={"X-Request-ID": "helloWorld"})
    assert result["request_id"] == "helloWorld"
    assert result["sub"]["request_id"] == "helloWorld"
