from abc import abstractmethod
from typing import Optional, Callable


class BaseBroadcaster(object):
    """
    Interface definition for message broadcasting implementation
    """
    @abstractmethod
    def subscribe(self, channel: str, callback: Callable) -> None: pass

    @abstractmethod
    def unsubscribe(self, channel: str) -> None: pass

    @abstractmethod
    def broadcast(self, channel: str, params: Optional[dict]=None, expect_answers: bool=False,
                  timeout: float=10) -> Optional[list]: pass
