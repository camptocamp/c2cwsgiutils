from c2cwsgiutils import stats


def test_outcome_timer_context_ok():
    backend = stats.MemoryBackend()
    stats.BACKENDS["memory"] = backend
    try:
        with stats.outcome_timer_context(["toto"]):
            pass

        assert set(backend._timers.keys()) == {"toto/success"}  # pylint: disable=W0212
        assert backend._timers["toto/success"][0] == 1  # pylint: disable=W0212
    finally:
        stats.BACKENDS = {}


class OkException(Exception):
    pass


def test_outcome_timer_context_failure():
    backend = stats.MemoryBackend()
    stats.BACKENDS["memory"] = backend
    try:
        with stats.outcome_timer_context(["toto"]):
            raise OkException("Boom")
        assert False
    except OkException:
        pass  # expected
    finally:
        stats.BACKENDS = {}

    assert set(backend._timers.keys()) == {"toto/failure"}  # pylint: disable=W0212
    assert backend._timers["toto/failure"][0] == 1  # pylint: disable=W0212


def test_format_tags():
    format_tags = stats._format_tags  # pylint: disable=W0212
    assert format_tags(None, "|", ",", "=", lambda x: x, lambda x: x) == ""
    assert format_tags({}, "|", ",", "=", lambda x: x, lambda x: x) == ""
    assert format_tags({"x": "a/b"}, "|", ",", "=", lambda x: x, lambda x: x.replace("/", "_")) == "|x=a_b"
    assert (
        format_tags({"x": "a", "y/z": "b"}, "|", ",", "=", lambda x: x.replace("/", "_"), lambda x: x)
        == "|x=a,y_z=b"
    )
