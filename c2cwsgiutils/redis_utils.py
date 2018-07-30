import logging
import redis.client  # noqa  # pylint: disable=unused-import
import redis.exceptions
import threading
import time
from typing import Optional  # noqa  # pylint: disable=unused-import

LOG = logging.getLogger(__name__)


class PubSubWorkerThread(threading.Thread):
    """
    A clone of redis.client.PubSubWorkerThread that doesn't die when the connections are broken.
    """
    def __init__(self, pubsub: redis.client.PubSub, name: Optional[str]=None) -> None:
        super().__init__(name=name)
        self.pubsub = pubsub
        self._running = False

    def run(self) -> None:
        if self._running:
            return
        self._running = True
        pubsub = self.pubsub
        last_was_ok = True
        while pubsub.subscribed:
            try:
                pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                last_was_ok = True
            except redis.exceptions.RedisError:
                if last_was_ok:
                    LOG.warning("Redis connection problem", exc_info=True)
                last_was_ok = False
                time.sleep(0.5)
        pubsub.close()
        self._running = False

    def stop(self) -> None:
        # stopping simply unsubscribes from all channels and patterns.
        # the unsubscribe responses that are generated will short circuit
        # the loop in run(), calling pubsub.close() to clean up the connection
        self.pubsub.unsubscribe()
        self.pubsub.punsubscribe()
