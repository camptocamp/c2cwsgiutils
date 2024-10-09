from collections.abc import Mapping, MutableMapping
from typing import Any, Callable, Optional

# noinspection PyProtectedMember
from c2cwsgiutils.broadcast import interface, utils


class LocalBroadcaster(interface.BaseBroadcaster):
    """Fake implementation of broadcasting messages (will just answer locally)."""

    def __init__(self) -> None:
        self._subscribers: MutableMapping[str, Callable[..., Any]] = {}

    def subscribe(self, channel: str, callback: Callable[..., Any]) -> None:
        self._subscribers[channel] = callback

    def unsubscribe(self, channel: str) -> None:
        del self._subscribers[channel]

    def broadcast(
        self, channel: str, params: Mapping[str, Any], expect_answers: bool, timeout: float
    ) -> Optional[list[Any]]:
        subscriber = self._subscribers.get(channel, None)
        answers = [utils.add_host_info(subscriber(**params))] if subscriber is not None else []
        return answers if expect_answers else None

    def get_subscribers(self) -> Mapping[str, Callable[..., Any]]:
        """Get the subscribers for testing purposes."""
        return self._subscribers
