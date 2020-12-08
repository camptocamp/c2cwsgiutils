import logging
import os
import threading
import time
from typing import Optional, Tuple

import redis.client
import redis.exceptions
import redis.sentinel
import yaml

LOG = logging.getLogger(__name__)

REDIS_URL_KEY = "C2C_REDIS_URL"
REDIS_OPTIONS_KEY = "C2C_REDIS_OPTIONS"
REDIS_SENTINELS_KEY = "C2C_REDIS_SENTINELS"
REDIS_SERVICENAME_KEY = "C2C_REDIS_SERVICENAME"
REDIS_DB_KEY = "C2C_REDIS_DB"

_master: Optional[redis.Redis] = None
_slave: Optional[redis.Redis] = None
_sentinel: Optional[redis.sentinel.Sentinel] = None


def get() -> Tuple[Optional[redis.Redis], Optional[redis.Redis], Optional[redis.sentinel.Sentinel]]:
    if _master is None:
        _init()
    return _master, _slave, _sentinel


def _init() -> None:
    global _master, _slave, _sentinel
    sentinels = os.environ.get(REDIS_SENTINELS_KEY)
    service_name = os.environ.get(REDIS_SERVICENAME_KEY)
    db = os.environ.get(REDIS_DB_KEY)
    url = os.environ.get(REDIS_URL_KEY)
    redis_options_ = os.environ.get(REDIS_OPTIONS_KEY)
    redis_options = (
        {}
        if redis_options_ is None
        else {
            e[0 : e.index("=")]: yaml.load(e[e.index("=") + 1 :], Loader=yaml.SafeLoader)
            for e in redis_options_.split(",")
        }
    )

    if sentinels:
        sentinels_str = [item.split(":") for item in sentinels.split(",")]
        _sentinel = redis.sentinel.Sentinel(
            [(e[0], int(e[1])) for e in sentinels_str],
            decode_responses=True,
            db=db,
            **redis_options,
        )

        try:
            LOG.info("Redis setup using: %s, %s, %s", sentinels, service_name, redis_options_)
            _master = _sentinel.master_for(service_name)
            _slave = _sentinel.slave_for(service_name)
            return
        except redis.sentinel.MasterNotFoundError:
            print(_sentinel.sentinels[0].sentinel_masters())
            raise Exception(_sentinel.sentinels[0].sentinel_masters())
    if url:
        if not url.startswith("redis://"):
            url = "redis://" + url

        LOG.info("Redis setup using: %s, with options: %s", url, redis_options_)
        _master = redis.Redis.from_url(url, decode_responses=True, **redis_options)  # type: ignore
        _slave = _master
    else:
        LOG.info(
            "No Redis configuration found, use %s or %s to configure it", REDIS_URL_KEY, REDIS_SENTINELS_KEY
        )


class PubSubWorkerThread(threading.Thread):
    """
    A clone of redis.client.PubSubWorkerThread that doesn't die when the connections are broken.
    """

    def __init__(self, pubsub: redis.client.PubSub, name: Optional[str] = None) -> None:
        super().__init__(name=name, daemon=True)
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
                if not last_was_ok:
                    LOG.info("Redis is back")
                    last_was_ok = True
            except redis.exceptions.RedisError:
                if last_was_ok:
                    LOG.warning("Redis connection problem", exc_info=True)
                last_was_ok = False
                time.sleep(0.5)
            except Exception:  # pylint: disable=broad-except
                LOG.warning("Unexpected error", exc_info=True)
        LOG.info("Redis subscription worker stopped")
        pubsub.close()
        self._running = False

    def stop(self) -> None:
        # stopping simply unsubscribes from all channels and patterns.
        # the unsubscribe responses that are generated will short circuit
        # the loop in run(), calling pubsub.close() to clean up the connection
        self.pubsub.unsubscribe()
        self.pubsub.punsubscribe()
