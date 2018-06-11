from c2cwsgiutils.broadcast import local
from c2cwsgiutils import broadcast


def test_local():
    broadcast._broadcaster = local.LocalBroadcaster()
    try:
        cb_calls = [0, 0]

        def cb1(data):
            cb_calls[0] += 1
            return data + 1

        def cb2(data):
            cb_calls[1] += 1

        assert broadcast.broadcast("test1", {'data': 1}, expect_answers=True) == []
        assert cb_calls == [0, 0]

        broadcast.subscribe("test1", cb1)
        broadcast.subscribe("test2", cb2)
        assert cb_calls == [0, 0]

        assert broadcast.broadcast("test1", {'data': 1}) is None
        assert cb_calls == [1, 0]

        assert broadcast.broadcast("test2", {'data': 1}) is None
        assert cb_calls == [1, 1]

        assert broadcast.broadcast("test1", {'data': 12}, expect_answers=True) == [13]
        assert cb_calls == [2, 1]

    finally:
        broadcast._broadcaster = None
