def test_without_secret(app_connection):
    content = app_connection.get('c2c')
    assert "Health checks" in content
    assert "Debug" not in content


def test_with_secret(app_connection):
    content = app_connection.get('c2c', params={'secret': 'changeme'})
    assert "Health checks" in content
    assert "Debug" in content
