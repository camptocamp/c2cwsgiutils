from c2cwsgiutils.acceptance.connection import Connection, CacheExpected


def test_pre_flight(app_connection: Connection):
    r = app_connection.options(
        "hello",
        cache_expected=CacheExpected.YES,
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-PINGOTHER, Content-Type",
        },
    )
    assert r.headers["Access-Control-Allow-Origin"] == "http://example.com"
    assert set(r.headers["Access-Control-Allow-Methods"].split(",")) == {
        "GET",
        "HEAD",
        "PUT",
        "POST",
        "OPTIONS",
    }
    assert set(r.headers["Access-Control-Allow-Headers"].split(",")) == {"X-PINGOTHER", "Content-Type"}
    assert r.headers["Access-Control-Max-Age"] == "86400"
    assert set(r.headers["Vary"].split(",")) == {"Origin"}
