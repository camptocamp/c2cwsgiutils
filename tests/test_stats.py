from c2cwsgiutils import stats


def test_outcome_timer_context_ok():
    backend = stats.MemoryBackend()
    stats.BACKENDS['memory'] = backend
    try:
        with stats.outcome_timer_context(['toto']):
            pass

        assert set(backend._timers.keys()) == {'toto/success'}   # pylint: disable=W0212
        assert backend._timers['toto/success'][0] == 1   # pylint: disable=W0212
    finally:
        stats.BACKENDS = {}


class OkException(Exception):
    pass


def test_outcome_timer_context_failure():
    backend = stats.MemoryBackend()
    stats.BACKENDS['memory'] = backend
    try:
        with stats.outcome_timer_context(['toto']):
            raise OkException("Boom")
        assert False
    except OkException:
        pass  # expected
    finally:
        stats.BACKENDS = {}

    assert set(backend._timers.keys()) == {'toto/failure'}   # pylint: disable=W0212
    assert backend._timers['toto/failure'][0] == 1   # pylint: disable=W0212
