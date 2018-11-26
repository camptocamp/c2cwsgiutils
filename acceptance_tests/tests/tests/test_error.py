def test_not_found(app_connection):
    error = app_connection.get_json('inexistant', expected_status=404)
    print("error=" + repr(error))
    assert error['status'] == 404


def test_http_error(app_connection):
    error = app_connection.get_json('error', params={'code': 403}, expected_status=403)
    assert error['status'] == 403
    assert error['message'] == 'bam'


def test_commit_time_db(app_connection):
    error = app_connection.get_json('error', params={'db': 'dup'}, expected_status=400)
    assert error['status'] == 400
    assert 'duplicate key' in error['message']


def test_db_data_error(app_connection):
    error = app_connection.get_json('error', params={'db': 'data'}, expected_status=400)
    assert error['status'] == 400
    assert 'invalid input syntax for integer' in error['message']


def test_401(app_connection):
    error = app_connection.get_raw("error", params={'code': 401}, expected_status=401)
    assert error.headers['WWW-Authenticate'].startswith('Basic')


def test_other(app_connection):
    error = app_connection.get_json('error', expected_status=500)
    assert error['status'] == 500
    assert error['message'] == 'boom'


def test_redirect_exception(app_connection):
    redirect = app_connection.get_raw('error', params={'code': 301}, expected_status=301,
                                      allow_redirects=False)
    assert redirect.headers['Location'] == 'http://www.camptocamp.com/en/'


def test_no_content_exception(app_connection):
    redirect = app_connection.get_raw('error', params={'code': 204}, expected_status=204)
    assert 'Content-Type' not in redirect.headers, redirect.headers['Content-Type']
    assert 'Content-Length' not in redirect.headers
