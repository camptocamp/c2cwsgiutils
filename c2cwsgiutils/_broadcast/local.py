from typing import Mapping, Callable  # noqa

from c2cwsgiutils._broadcast import utils, interface


class LocalBroadcaster(interface.BaseBroadcaster):
    """
    Fake implementation of broadcasting messages (will just answer locally)
    """
    def __init__(self):
        self._subscribers = {}  # type: Mapping[str, Callable]

    def subscribe(self, channel, callback):
        self._subscribers[channel] = callback

    def unsubscribe(self, channel):
        del self._subscribers[channel]

    def broadcast(self, channel, params, expect_answers, _timeout):
        subscriber = self._subscribers.get(channel, None)
        answers = [utils.add_host_info(subscriber(**params))] if subscriber is not None else []
        return answers if expect_answers else None
