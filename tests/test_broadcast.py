import pytest
from c2cwsgiutils import broadcast
from c2cwsgiutils.broadcast import local


@pytest.fixture()
def local_broadcaster():
    broadcast._broadcaster = local.LocalBroadcaster()  # pylint: disable=W0212
    try:
        yield
    finally:
        broadcast._broadcaster = None  # pylint: disable=W0212


def test_local(local_broadcaster):
    cb_calls = [0, 0]

    def cb1(data):
        cb_calls[0] += 1
        return data + 1

    def cb2():
        cb_calls[1] += 1

    assert broadcast.broadcast("test1", {"data": 1}, expect_answers=True) == []
    assert cb_calls == [0, 0]

    broadcast.subscribe("test1", cb1)
    broadcast.subscribe("test2", cb2)
    assert cb_calls == [0, 0]

    assert broadcast.broadcast("test1", {"data": 1}) is None
    assert cb_calls == [1, 0]

    assert broadcast.broadcast("test2") is None
    assert cb_calls == [1, 1]

    assert broadcast.broadcast("test1", {"data": 12}, expect_answers=True) == [13]
    assert cb_calls == [2, 1]

    broadcast.unsubscribe("test1")
    assert broadcast.broadcast("test1", {"data": 1}, expect_answers=True) == []
    assert cb_calls == [2, 1]


def test_decorator(local_broadcaster):
    cb_calls = [0, 0]

    @broadcast.decorator(expect_answers=True)
    def cb1(value):
        cb_calls[0] += 1
        return value + 1

    @broadcast.decorator(channel="test3")
    def cb2():
        cb_calls[1] += 1

    assert cb1(value=12) == [13]
    assert cb_calls == [1, 0]

    assert cb2() is None
    assert cb_calls == [1, 1]


def test_fallback():
    cb_calls = [0]

    def cb1(value):
        cb_calls[0] += 1
        return value + 1

    try:
        broadcast.subscribe("test1", cb1)

        assert broadcast.broadcast("test1", {"value": 12}, expect_answers=True) == [13]
        assert cb_calls == [1]
    finally:
        broadcast._broadcaster = None  # pylint: disable=W0212
