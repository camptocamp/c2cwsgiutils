def _switch(app_connection, enable=None):
    params = {'secret': 'changeme'}
    if enable is not None:
        params['enable'] = "1" if enable else "0"
    answer = app_connection.get_json("c2c/sql_profiler", params=params)
    assert answer['status'] == 200
    return answer['enabled']


def test_ok(app_connection, slave_db_connection):
    assert _switch(app_connection) is False
    assert _switch(app_connection, enable=True) is True
    try:
        assert _switch(app_connection) is True
        app_connection.get_json("hello")
    finally:
        _switch(app_connection, enable=False)


def test_no_secret(app_connection):
    app_connection.get_json("c2c/sql_profiler", params={'enable': '1'}, expected_status=403)
