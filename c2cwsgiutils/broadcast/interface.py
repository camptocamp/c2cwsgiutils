from abc import abstractmethod
from typing import Any, Callable, List, Mapping, Optional


class BaseBroadcaster:
    """Interface definition for message broadcasting implementation."""

    @abstractmethod
    def subscribe(self, channel: str, callback: Callable[..., Any]) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def unsubscribe(self, channel: str) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def broadcast(
        self, channel: str, params: Mapping[str, Any], expect_answers: bool, timeout: float
    ) -> Optional[List[Any]]:
        pass  # pragma: no cover
