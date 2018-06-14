from abc import abstractmethod
from typing import Optional, Callable, Mapping, Any  # noqa  # pylint: disable=unused-import


class BaseBroadcaster(object):
    """
    Interface definition for message broadcasting implementation
    """
    @abstractmethod
    def subscribe(self, channel: str, callback: Callable) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def unsubscribe(self, channel: str) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def broadcast(self, channel: str, params: Mapping[str, Any], expect_answers: bool,
                  timeout: float) -> Optional[list]:
        pass  # pragma: no cover
