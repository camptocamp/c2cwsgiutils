from c2cwsgiutils.acceptance import retry


@retry(Exception)
def test_ok(app_connection):
    # reset the stats to be sure where we are at
    app_connection.get_json('c2c/stats.json?reset=1', cors=False)

    app_connection.get_json("hello")  # to be sure we have some stats

    stats = app_connection.get_json('c2c/stats.json', cors=False)
    print(stats)
    assert stats['timers']['render/group=2/method=GET/route=hello/status=200']['nb'] == 1
    assert stats['timers']['route/group=2/method=GET/route=hello/status=200']['nb'] == 1
    assert stats['timers']['sql/read_hello']['nb'] == 1
    assert stats['timers']['sql/query=SELECT FROM hello LIMIT ?']['nb'] == 1
    assert stats['gauges']['test/gauge_s/toto=tutu/value=24'] == 42
    assert stats['counters']['test/counter'] == 1


def test_server_timing(app_connection):
    r = app_connection.get_raw('hello')
    assert 'Server-Timing' in r.headers


def test_requests(app_connection):
    # reset the stats to be sure where we are at
    app_connection.get_json('c2c/stats.json?reset=1', cors=False)

    app_connection.get_json('tracking/1')

    stats = app_connection.get_json('c2c/stats.json', cors=False)
    print(stats)
    assert stats['timers']['requests/host=localhost/method=GET/port=8080/scheme=http/status=200']['nb'] == 1


def test_redis(app_connection):
    # reset the stats to be sure where we are at
    app_connection.get_json('c2c/stats.json?reset=1', cors=False)

    # that sends a few PUBLISH to redis
    app_connection.get_json('c2c/debug/stacks', params={'secret': 'changeme'})

    stats = app_connection.get_json('c2c/stats.json', cors=False)
    print(stats)
    assert stats['timers']['redis/cmd=PUBLISH/success=1']['nb'] >= 1


def test_version(app_connection):
    app_connection.get_json("c2c/health_check", params={'checks': 'version', 'max_level': '10'})
    version = app_connection.get_json('c2c/versions.json')
    stats = app_connection.get_json('c2c/stats.json', cors=False)
    print(stats)
    assert stats['gauges']['version/version=' + version['main']['git_hash']] == 1
