import json


def _remove_timings(response):
    for status in ('successes', 'failures'):
        assert status in response
        for key, value in response[status].items():
            assert 'timing' in value
            del value['timing']
    return response


def test_ok(app_connection):
    response = app_connection.get_json("c2c/health_check")
    print('response=' + json.dumps(response))
    assert _remove_timings(response) == {
        'successes': {
            'db_engine_sqlalchemy': {},
            'db_engine_sqlalchemy_slave': {},
            'http://localhost:8080/api/hello': {},
            'fun_url': {},
            'alembic_app_alembic.ini_alembic': {'result': '4a8c1bb4e775'}
        },
        'failures': {},
    }


def test_filter(app_connection):
    response = app_connection.get_json("c2c/health_check", params={'checks': 'db_engine_sqlalchemy,fun_url'})
    print('response=' + json.dumps(response))
    assert _remove_timings(response) == {
        'successes': {
            'db_engine_sqlalchemy': {},
            'fun_url': {}
        },
        'failures': {},
    }


def test_failure(app_connection):
    response = app_connection.get_json("c2c/health_check", params={'max_level': '2'}, expected_status=500)
    print('response=' + json.dumps(response))
    assert _remove_timings(response) == {
        'successes': {
            'db_engine_sqlalchemy': {},
            'db_engine_sqlalchemy_slave': {},
            'http://localhost:8080/api/hello': {},
            'fun_url': {},
            'alembic_app_alembic.ini_alembic': {'result': '4a8c1bb4e775'}
        },
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
        'successes': {},
        'failures': {}
    }
