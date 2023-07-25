from c2cwsgiutils.acceptance import utils


def test_without_secret(app_connection):
    content = app_connection.get("c2c", cors=False)
    assert "Health checks" in content
    assert "Debug" not in content


def test_with_secret(app_connection):
    content = app_connection.get("c2c", params={"secret": "changeme"}, cors=False)
    assert "Health checks" in content
    assert "Debug" in content

    # a cookie should keep us logged in
    app_connection.get("c2c", cors=False)
    assert "Health checks" in content
    assert "Debug" in content


def test_https(app_connection):
    content = app_connection.get(
        "c2c", params={"secret": "changeme"}, headers={"X-Forwarded-Proto": "https"}, cors=False
    )
    assert "https://app:8080/api/" in content
    assert "http://app:8080/api/" not in content


def test_with_slash(app_connection):
    content = app_connection.get("c2c/", cors=False)
    assert "Health checks" in content
