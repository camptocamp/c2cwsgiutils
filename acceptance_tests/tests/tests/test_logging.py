def test_api(app_connection):
    response = app_connection.get_json('c2c/logging/level',
                                       params={'secret': 'changeme', 'name': 'sqlalchemy.engine'})
    assert response == {'status': 200, 'name': 'sqlalchemy.engine', 'level': 'DEBUG',
                        'effective_level': 'DEBUG'}

    response = app_connection.get_json('c2c/logging/level',
                                       params={'secret': 'changeme', 'name': 'sqlalchemy.engine.sub'})
    assert response == {'status': 200, 'name': 'sqlalchemy.engine.sub', 'level': 'NOTSET',
                        'effective_level': 'DEBUG'}

    response = app_connection.get_json('c2c/logging/level',
                                       params={'secret': 'changeme', 'name': 'sqlalchemy.engine',
                                               'level': 'INFO'})
    assert response == {'status': 200, 'name': 'sqlalchemy.engine', 'level': 'INFO',
                        'effective_level': 'INFO'}

    response = app_connection.get_json('c2c/logging/level',
                                       params={'secret': 'changeme', 'name': 'sqlalchemy.engine'})
    assert response == {'status': 200, 'name': 'sqlalchemy.engine', 'level': 'INFO',
                        'effective_level': 'INFO'}

    response = app_connection.get_json('c2c/logging/level',
                                       params={'secret': 'changeme', 'name': 'sqlalchemy.engine.sub'})
    assert response == {'status': 200, 'name': 'sqlalchemy.engine.sub', 'level': 'NOTSET',
                        'effective_level': 'INFO'}

    response = app_connection.get_json('c2c/logging/level',
                                       params={'secret': 'changeme', 'name': 'sqlalchemy.engine',
                                               'level': 'DEBUG'})
    assert response == {'status': 200, 'name': 'sqlalchemy.engine', 'level': 'DEBUG',
                        'effective_level': 'DEBUG'}


def test_api_bad_secret(app_connection):
    app_connection.get_json('c2c/logging/level', params={'secret': 'wrong', 'name': 'sqlalchemy.engine'},
                            expected_status=403)


def test_api_missing_secret(app_connection):
    app_connection.get_json('c2c/logging/level', params={'name': 'sqlalchemy.engine'}, expected_status=403)
