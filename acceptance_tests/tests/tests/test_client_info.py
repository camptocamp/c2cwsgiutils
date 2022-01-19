import json
import os

import pytest

EXPECTED = {
    "client_addr": "1.1.1.1",
    "host": "example.com",
    "host_port": "443",
    "http_version": "HTTP/1.1",
    "path": "/api/c2c/debug/headers",
    "path_info": "/api/c2c/debug/headers",
    "remote_addr": "1.1.1.1",
    "remote_host": None,
    "scheme": "https",
    "server_name": "0.0.0.0",
    "server_port": 8080,
}


@pytest.mark.skipif(os.environ.get("WAITRESS", "FALSE") == "TRUE", reason="Not working on waitress")
def test_forwarded_openshift(app_connection):
    response = app_connection.get_json(
        "c2c/debug/headers",
        params={"secret": "changeme"},
        headers={
            "Forwarded": "for=1.1.1.1;host=example.com;proto=https;proto-version=h2",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto-Version": "h2",
        },
        cors=False,
    )
    print("response=" + json.dumps(response, indent=4))
    assert response["client_info"] == EXPECTED


@pytest.mark.skipif(os.environ.get("WAITRESS", "FALSE") == "TRUE", reason="Not working on waitress")
def test_forwarded_haproxy(app_connection):
    response = app_connection.get_json(
        "c2c/debug/headers",
        params={"secret": "changeme"},
        headers={
            "X-Forwarded-Host": "example.com",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-For": "1.1.1.1",
        },
        cors=False,
    )
    print("response=" + json.dumps(response, indent=4))
    assert response["client_info"] == EXPECTED
