def test_pretty_print(app_connection):
    response = app_connection.get_raw('c2c/versions.json')
    print("response=" + response.text)
    assert '\n' in response.text
