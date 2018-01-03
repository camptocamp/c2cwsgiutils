from c2cwsgiutils.acceptance import retry


@retry(Exception)
def test_ok(app_connection):
    # reset the stats to be sure where we are at
    app_connection.get_json('c2c/stats.json?reset=1', cors=False)

    app_connection.get_json("hello")  # to be sure we have some stats

    stats = app_connection.get_json('c2c/stats.json', cors=False)
    print(stats)
    assert stats['timers']['render/GET/hello/200']['nb'] == 1
    assert stats['timers']['route/GET/hello/200']['nb'] == 1
    assert stats['timers']['sql/read_hello']['nb'] == 1
    assert stats['timers']['sql/SELECT FROM hello LIMIT ?']['nb'] == 1
    assert stats['gauges']['test/gauge_s'] == 42
    assert stats['counters']['test/counter'] == 1


def test_server_timing(app_connection):
    r = app_connection.get_raw('hello')
    assert 'Server-Timing' in r.headers
