def test_default(app_connection):
    response = app_connection.get_raw('c2c/versions.json')
    assert '\n' not in response.text


def test_pretty(app_connection):
    response = app_connection.get_raw('c2c/versions.json', params={'c2c_pretty': "1"})
    print("response=" + response.text)
    assert '\n' in response.text
