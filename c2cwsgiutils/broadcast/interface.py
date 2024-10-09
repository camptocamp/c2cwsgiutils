from abc import abstractmethod
from collections.abc import Mapping
from typing import Any, Callable, Optional


class BaseBroadcaster:
    """Interface definition for message broadcasting implementation."""

    @abstractmethod
    def subscribe(self, channel: str, callback: Callable[..., Any]) -> None:
        """Subscribe to a channel."""

    @abstractmethod
    def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""

    @abstractmethod
    def broadcast(
        self, channel: str, params: Mapping[str, Any], expect_answers: bool, timeout: float
    ) -> Optional[list[Any]]:
        """Broadcast a message to a channel."""
