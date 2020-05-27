import json
import time


def test_stacks(app_connection):
    stacks = app_connection.get_json("c2c/debug/stacks", params={"secret": "changeme"}, cors=False)
    _check_stacks(stacks)


def _check_stacks(stacks):
    print("stacks=" + json.dumps(stacks, indent=4))
    assert "c2cwsgiutils/debug" in json.dumps(stacks)


def test_header_auth(app_connection):
    stacks = app_connection.get_json("c2c/debug/stacks", headers={"X-API-Key": "changeme"}, cors=False)
    _check_stacks(stacks)


def test_no_auth(app_connection):
    app_connection.get_json("c2c/debug/stacks", expected_status=403, cors=False)


def test_memory(app_connection):
    memory = app_connection.get_json("c2c/debug/memory", params={"secret": "changeme"}, cors=False)
    print("memory=" + json.dumps(memory, indent=4))
    assert len(memory) == 1


def test_memory_analyze_functions(app_connection):
    class_ = "builtins.function"
    memory = app_connection.get_json(
        "c2c/debug/memory", params={"secret": "changeme", "analyze_type": class_}, cors=False
    )
    print("memory=" + json.dumps(memory, indent=4))
    assert len(memory) == 1
    assert class_ in memory[0]
    assert "modules" in memory[0][class_]
    assert "timeout" not in memory[0][class_]


def test_memory_analyze_other(app_connection):
    class_ = "gunicorn.six.MovedAttribute"
    memory = app_connection.get_json(
        "c2c/debug/memory", params={"secret": "changeme", "analyze_type": class_}, cors=False
    )
    print("memory=" + json.dumps(memory, indent=4))
    assert len(memory) == 1
    assert class_ in memory[0]
    assert "biggest_objects" in memory[0][class_]
    assert "timeout" not in memory[0][class_]


def test_sleep(app_connection):
    start_time = time.monotonic()
    app_connection.get(
        "c2c/debug/sleep", params={"secret": "changeme", "time": "0.1"}, expected_status=204, cors=False
    )
    assert time.monotonic() - start_time > 0.1


def test_time(app_connection):
    time_ = app_connection.get_json("c2c/debug/time", cors=False)
    assert time_["timezone"] == "UTC"  # run in docker -> UTC


def test_headers(app_connection):
    response = app_connection.get_json(
        "c2c/debug/headers", params={"secret": "changeme"}, headers={"X-Toto": "42"}, cors=False
    )
    print("response=" + json.dumps(response, indent=4))
    assert response["headers"]["X-Toto"] == "42"


def _check_leak_there(response):
    print("response=" + json.dumps(response, indent=4))
    leaked = {v[0]: v[2] for v in response}
    assert leaked["c2cwsgiutils_app.services.LeakedObject"] == 1


def test_memory_diff(app_connection):
    response = app_connection.get_json(
        "c2c/debug/memory_diff", params={"secret": "changeme", "path": "/api/ping?toto=tutu"}, cors=False
    )
    _check_leak_there(response)


def test_memory_diff_deprecated(app_connection):
    response = app_connection.get_json(
        "c2c/debug/memory_diff/api/ping", params={"secret": "changeme"}, cors=False
    )
    _check_leak_there(response)


def test_error(app_connection):
    app_connection.get_json(
        "c2c/debug/error", params={"secret": "changeme", "status": "500"}, expected_status=500, cors=False
    )


def test_memory_maps(app_connection):
    memory = app_connection.get_json("c2c/debug/memory_maps", params={"secret": "changeme"}, cors=False)
    print("memory_maps=" + json.dumps(memory, indent=4))
    assert len(memory) > 0


def test_show_refs(app_connection):
    refs = app_connection.get(
        "c2c/debug/show_refs.dot",
        params=dict(
            secret="changeme",
            analyze_type="gunicorn.app.wsgiapp.WSGIApplication",
            max_depth="3",
            too_many="10",
        ),
        cors=False,
    )
    print("refs=" + refs)
    assert "WSGIApplication" in refs
