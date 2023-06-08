import re

_PID_RE = re.compile(r',pid="([0-9]+)"')


def test_prometheus(prometheus_connection):
    # One for the root process, one for each workers
    assert (
        len(set(_PID_RE.findall(prometheus_connection.get("metrics", cache_expected=False, cors=False)))) == 3
    )
