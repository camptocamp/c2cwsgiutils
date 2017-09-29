import json


def test_stacks(app_connection):
    stacks = app_connection.get('c2c/debug/stacks', params={'secret': 'changeme'})
    assert 'c2cwsgiutils/debug' in stacks


def test_header_auth(app_connection):
    stacks = app_connection.get('c2c/debug/stacks', headers={'X-API-Key': 'changeme'})
    assert 'c2cwsgiutils/debug' in stacks


def test_no_auth(app_connection):
    app_connection.get_json('c2c/debug/stacks', expected_status=403)


def test_memory(app_connection):
    memory = app_connection.get_json('c2c/debug/memory', params={'secret': 'changeme'})
    print("memory=" + json.dumps(memory, indent=4))
