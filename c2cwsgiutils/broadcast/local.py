from collections.abc import Callable, Mapping, MutableMapping
from typing import Any

# noinspection PyProtectedMember
from c2cwsgiutils.broadcast import interface, utils


class LocalBroadcaster(interface.BaseBroadcaster):
    """Fake implementation of broadcasting messages (will just answer locally)."""

    def __init__(self) -> None:
        """Initialize the broadcaster."""
        self._subscribers: MutableMapping[str, Callable[..., Any]] = {}

    def subscribe(self, channel: str, callback: Callable[..., Any]) -> None:
        """Subscribe to a channel."""
        self._subscribers[channel] = callback

    def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        del self._subscribers[channel]

    def broadcast(
        self,
        channel: str,
        params: Mapping[str, Any],
        expect_answers: bool,
        timeout: float,
    ) -> list[Any] | None:
        """Broadcast a message to all the listeners."""
        del timeout  # Not used
        subscriber = self._subscribers.get(channel, None)
        answers = [utils.add_host_info(subscriber(**params))] if subscriber is not None else []
        return answers if expect_answers else None

    def get_subscribers(self) -> Mapping[str, Callable[..., Any]]:
        """Get the subscribers for testing purposes."""
        return self._subscribers
