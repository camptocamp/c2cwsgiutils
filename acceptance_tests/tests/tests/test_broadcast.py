def test_broadcast_reconfig(app_connection):
    response = app_connection.get_json("broadcast", cors=False)
    assert response == [42]  # only one worker
