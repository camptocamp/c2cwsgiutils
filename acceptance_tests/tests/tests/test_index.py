from c2cwsgiutils.acceptance import utils


def test_without_secret(app_connection):
    content = app_connection.get('c2c')
    assert "Health checks" in content
    assert "Debug" not in content


def test_with_secret(app_connection):
    content = app_connection.get('c2c', params={'secret': 'changeme'})
    assert "Health checks" in content
    assert "Debug" in content

    # a cookie should keep us logged in
    app_connection.get('c2c')
    assert "Health checks" in content
    assert "Debug" in content


def test_https(app_connection):
    content = app_connection.get('c2c', params={'secret': 'changeme'},
                                 headers={'X-Forwarded-Proto': 'https'})
    assert 'https://' + utils.DOCKER_GATEWAY + ':8480/api/' in content
    assert 'http://' + utils.DOCKER_GATEWAY + ':8480/api/' not in content


def test_with_slash(app_connection):
    content = app_connection.get('c2c/')
    assert "Health checks" in content
