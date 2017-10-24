import json


def test_ok(app_connection):
    response = app_connection.get_json("c2c/health_check")
    print('response=' + json.dumps(response))
    assert response == {
        'status': 200,
        'successes': ['db_engine_sqlalchemy', 'db_engine_sqlalchemy_slave', 'http://localhost/api/hello',
                      'fun_url',  'alembic_app_alembic.ini'],
        'failures': {},
        'timings': response['timings']
    }
    assert response['timings'].keys() == {
        'db_engine_sqlalchemy', 'db_engine_sqlalchemy_slave', 'http://localhost/api/hello',
        'fun_url',  'alembic_app_alembic.ini'}


def test_filter(app_connection):
    response = app_connection.get_json("c2c/health_check", params={'checks': 'db_engine_sqlalchemy,fun_url'})
    print('response=' + json.dumps(response))
    assert response == {
        'status': 200,
        'successes': ['db_engine_sqlalchemy', 'fun_url'],
        'failures': {},
        'timings': response['timings']
    }
    assert response['timings'].keys() == {'db_engine_sqlalchemy', 'fun_url'}


def test_failure(app_connection):
    response = app_connection.get_json("c2c/health_check", params={'max_level': '2'}, expected_status=500)
    print('response=' + json.dumps(response))
    assert response == {
        'status': 500,
        'successes': ['db_engine_sqlalchemy', 'db_engine_sqlalchemy_slave', 'http://localhost/api/hello',
                      'fun_url', 'alembic_app_alembic.ini'],
        'failures': {
            'fail': {
                'message': 'failing check',
                'stacktrace': response['failures']['fail']['stacktrace']
            }
        },
        'timings': response['timings']
    }
    assert response['timings'].keys() == {
        'db_engine_sqlalchemy', 'db_engine_sqlalchemy_slave', 'http://localhost/api/hello',
        'fun_url', 'alembic_app_alembic.ini', 'fail'}


def test_ping(app_connection):
    response = app_connection.get_json("c2c/health_check", params={'max_level': '0'})
    print('response=' + json.dumps(response))
    assert response == {
        'status': 200,
        'successes': [],
        'failures': {},
        'timings': {}
    }
