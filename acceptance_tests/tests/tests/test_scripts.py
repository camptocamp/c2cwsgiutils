def test_get_hello(composition, master_db_setup, slave_db_setup):
    logs = composition.exec("app", "get-hello").splitlines()
    filtered = []
    for line in logs:
        if line.startswith("{"):
            continue
        if line == "The environment variable 'test' is duplicated with different case, ignoring":
            continue
        if "Blowfish" in line:
            continue
        filtered.append(line)

    assert filtered == ["master"]
