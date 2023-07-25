def test_get_hello(composition):
    logs = composition.exec("app", "get-hello").splitlines()
    logs = [o for o in logs if not o.startswith("{")]
    print("\n".join(logs))
    logs = [o for o in logs if o == "master"]
    assert len(logs) == 1
