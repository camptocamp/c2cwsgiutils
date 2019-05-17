import json
import time


def test_stacks(app_connection):
    stacks = app_connection.get_json('c2c/debug/stacks', params={'secret': 'changeme'})
    _check_stacks(stacks)


def _check_stacks(stacks):
    print("stacks=" + json.dumps(stacks, indent=4))
    assert 'c2cwsgiutils/debug' in json.dumps(stacks)


def test_header_auth(app_connection):
    stacks = app_connection.get_json('c2c/debug/stacks', headers={'X-API-Key': 'changeme'})
    _check_stacks(stacks)


def test_no_auth(app_connection):
    app_connection.get_json('c2c/debug/stacks', expected_status=403)


def test_memory(app_connection):
    memory = app_connection.get_json('c2c/debug/memory', params={'secret': 'changeme'})
    print("memory=" + json.dumps(memory, indent=4))
    assert len(memory) == 1


def test_sleep(app_connection):
    start_time = time.monotonic()
    app_connection.get('c2c/debug/sleep', params={'secret': 'changeme', 'time': '0.1'},
                       expected_status=204)
    assert time.monotonic() - start_time > 0.1


def test_time(app_connection):
    time_ = app_connection.get_json('c2c/debug/time')
    assert time_['timezone'] == 'UTC'  # run in docker -> UTC


def test_headers(app_connection):
    response = app_connection.get_json('c2c/debug/headers', params={'secret': 'changeme'},
                                       headers={'X-Toto': '42'})
    print("response=" + json.dumps(response, indent=4))
    assert response['headers']['X-Toto'] == '42'


def _check_leak_there(response):
    print("response=" + json.dumps(response, indent=4))
    leaked = {v[0]: v[2] for v in response}
    assert leaked['c2cwsgiutils_app.services.LeakedObject'] == 1


def test_memory_diff(app_connection):
    response = app_connection.get_json('c2c/debug/memory_diff', params={
        'secret': 'changeme',
        'path': '/api/ping?toto=tutu'
    })
    _check_leak_there(response)


def test_memory_diff_deprecated(app_connection):
    response = app_connection.get_json('c2c/debug/memory_diff/api/ping', params={'secret': 'changeme'})
    _check_leak_there(response)


def test_error(app_connection):
    app_connection.get_json('c2c/debug/error', params={'secret': 'changeme', 'status': '500'},
                            expected_status=500)
