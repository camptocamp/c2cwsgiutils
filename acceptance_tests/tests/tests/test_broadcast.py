def test_broadcast_reconfig(app_connection):
    response = app_connection.get_json("broadcast")
    assert response == [42]  # only one worker
