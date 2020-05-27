def test_slave(app_connection, slave_db_connection):
    assert app_connection.get_json("hello") == {"value": "slave"}


def test_master(app_connection, master_db_connection):
    assert app_connection.put_json("hello") == {"value": "master"}


def test_forced_slave(app_connection, slave_db_connection):
    assert app_connection.post_json("hello") == {"value": "slave"}
