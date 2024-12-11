import re

_PID_RE = re.compile(r',pid="([0-9]+)"')


def test_prometheus_1(prometheus_1_connection):
    # One for the root process, one for each workers (1)
    assert (
        len(set(_PID_RE.findall(prometheus_1_connection.get("metrics", cache_expected=False, cors=False))))
        == 2
    )


def test_prometheus_2(prometheus_2_connection):
    # One for the root process, one for each workers
    metrics = prometheus_2_connection.get("metrics", cache_expected=False, cors=False)
    assert len(set(_PID_RE.findall(metrics))) == 0
    assert re.search(r"^c2cwsgiutils_python_resource\{.*", metrics, re.MULTILINE) is not None
    assert re.search(r"^c2cwsgiutils_python_memory_info\{.*", metrics, re.MULTILINE) is not None
