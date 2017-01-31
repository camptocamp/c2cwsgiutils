def test_ok(app_connection):
    app_connection.get_json("hello")  # to be sure we have some stats
    stats = app_connection.get_json('stats.json', cors=False)
    print(stats)
    assert 'render/GET/hello/200' in stats['timers']
    assert 'route/GET/hello/200' in stats['timers']
    assert 'sql/SELECT_FROM_hello_LIMIT_?'
