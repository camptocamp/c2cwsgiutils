import json


def test_ok(app_connection):
    response = app_connection.get_json("c2c/health_check")
    print('response=' + json.dumps(response))
    assert response == {
        'status': 200,
        'successes': ['db_engine_sqlalchemy', 'db_engine_sqlalchemy_slave', 'http://localhost/api/hello'],
        'failures': {}
    }


def test_failure(app_connection):
    response = app_connection.get_json("c2c/health_check", params={'max_level': '2'}, expected_status=500)
    print('response=' + json.dumps(response))
    assert response == {
        'status': 500,
        'successes': ['db_engine_sqlalchemy', 'db_engine_sqlalchemy_slave', 'http://localhost/api/hello'],
        'failures': {
            'fail': {
                'message': 'failing check',
                'stacktrace': response['failures']['fail']['stacktrace']
            }
        }
    }


def test_ping(app_connection):
    response = app_connection.get_json("c2c/health_check", params={'max_level': '0'})
    print('response=' + json.dumps(response))
    assert response == {
        'status': 200,
        'successes': [],
        'failures': {}
    }
