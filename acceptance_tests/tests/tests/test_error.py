def test_not_found(app_connection):
    error = app_connection.get_json('inexistant', expected_status=404)
    print("error=" + repr(error))
    assert error['status'] == 404


def test_http_error(app_connection):
    error = app_connection.get_json('error', params={'code': 403}, expected_status=403)
    assert error['status'] == 403
    assert error['message'] == 'bam'


def test_commit_time_db(app_connection):
    error = app_connection.get_json('error', params={'db': '1'}, expected_status=400)
    assert error['status'] == 400
    assert 'duplicate key' in error['message']


def test_other(app_connection):
    error = app_connection.get_json('error', expected_status=500)
    assert error['status'] == 500
    assert error['message'] == 'boom'
