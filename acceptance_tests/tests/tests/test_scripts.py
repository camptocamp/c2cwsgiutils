def test_get_hello(composition):
    logs = composition.exec("app", "get-hello").splitlines()
    logs = [o for o in logs if not o.startswith("{")]
    logs = [
        o for o in logs if o != "The environment variable 'test' is duplicated with different case, ignoring"
    ]
    assert logs[0] == "master"
