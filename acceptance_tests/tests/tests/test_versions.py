def test_ok(app_connection):
    response = app_connection.get_json('versions.json')
    assert 'main' in response
    assert 'git_hash' in response['main']
    assert 'packages' in response
    assert 'pyramid' in response['packages']
