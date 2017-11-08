from c2cwsgiutils._broadcast import local
from c2cwsgiutils import _broadcast


def test_local():
    _broadcast._broadcaster = local.LocalBroadcaster()  # pylint: disable=W0212
    try:
        cb_calls = [0, 0]

        def cb1(data):
            cb_calls[0] += 1
            return data + 1

        def cb2(data):
            cb_calls[1] += 1

        assert _broadcast.broadcast("test1", {'data': 1}, expect_answers=True) == []  # pylint: disable=W0212
        assert cb_calls == [0, 0]

        _broadcast.subscribe("test1", cb1)
        _broadcast.subscribe("test2", cb2)
        assert cb_calls == [0, 0]

        assert _broadcast.broadcast("test1", {'data': 1}) is None
        assert cb_calls == [1, 0]

        assert _broadcast.broadcast("test2", {'data': 1}) is None
        assert cb_calls == [1, 1]

        assert _broadcast.broadcast("test1", {'data': 12}, expect_answers=True) == [13]
        assert cb_calls == [2, 1]

    finally:
        _broadcast._broadcaster = None  # pylint: disable=W0212
