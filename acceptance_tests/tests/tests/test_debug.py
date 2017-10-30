import json
import time


def test_stacks(app_connection):
    stacks = app_connection.get_json('c2c/debug/stacks', params={'secret': 'changeme'})
    _check_stacks(stacks)


def _check_stacks(stacks):
    assert len(stacks) == 5
    print("stacks=" + json.dumps(stacks, indent=4))
    for proc_stacks in stacks:
        assert 'c2cwsgiutils/debug' in json.dumps(proc_stacks)


def test_header_auth(app_connection):
    stacks = app_connection.get_json('c2c/debug/stacks', headers={'X-API-Key': 'changeme'})
    _check_stacks(stacks)


def test_no_auth(app_connection):
    app_connection.get_json('c2c/debug/stacks', expected_status=403)


def test_memory(app_connection):
    memory = app_connection.get_json('c2c/debug/memory', params={'secret': 'changeme'})
    print("memory=" + json.dumps(memory, indent=4))
    assert len(memory) == 5


def test_sleep(app_connection):
    start_time = time.monotonic()
    app_connection.get('c2c/debug/sleep', params={'secret': 'changeme', 'time': '0.1'},
                       expected_status=204)
    assert time.monotonic() - start_time > 0.1


def test_headers(app_connection):
    response = app_connection.get_json('c2c/debug/headers', params={'secret': 'changeme'},
                                       headers={'X-Toto': '42'})
    print("response=" + json.dumps(response, indent=4))
    assert response['X-Toto'] == '42'
