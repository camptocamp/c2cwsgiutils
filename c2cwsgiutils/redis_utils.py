import logging
import threading
import time
from typing import Any, Mapping, Optional, Tuple

import redis.client
import redis.exceptions
import redis.sentinel
import yaml

import c2cwsgiutils.config_utils

LOG = logging.getLogger(__name__)

REDIS_URL_KEY = "C2C_REDIS_URL"
REDIS_OPTIONS_KEY = "C2C_REDIS_OPTIONS"
REDIS_SENTINELS_KEY = "C2C_REDIS_SENTINELS"
REDIS_SERVICENAME_KEY = "C2C_REDIS_SERVICENAME"
REDIS_DB_KEY = "C2C_REDIS_DB"

REDIS_URL_KEY_PROP = "c2c.redis_url"
REDIS_OPTIONS_KEY_PROP = "c2c.redis_options"
REDIS_SENTINELS_KEY_PROP = "c2c.redis_sentinels"
REDIS_SERVICENAME_KEY_PROP = "c2c.redis_servicename"
REDIS_DB_KEY_PROP = "c2c.redis_db"

_master: Optional["redis.client.Redis[str]"] = None  # pylint: disable=unsubscriptable-object
_slave: Optional["redis.client.Redis[str]"] = None  # pylint: disable=unsubscriptable-object
_sentinel: Optional[redis.sentinel.Sentinel] = None


def get(
    settings: Optional[Mapping[str, bytes]] = None,
) -> Tuple[
    Optional["redis.client.Redis[str]"],  # pylint: disable=unsubscriptable-object
    Optional["redis.client.Redis[str]"],  # pylint: disable=unsubscriptable-object
    Optional[redis.sentinel.Sentinel],
]:
    if _master is None:
        _init(settings)
    return _master, _slave, _sentinel


def _init(settings: Optional[Mapping[str, Any]]) -> None:
    global _master, _slave, _sentinel
    sentinels = c2cwsgiutils.config_utils.env_or_settings(
        settings, REDIS_SENTINELS_KEY, REDIS_SENTINELS_KEY_PROP
    )
    service_name = c2cwsgiutils.config_utils.env_or_settings(
        settings, REDIS_SERVICENAME_KEY, REDIS_SERVICENAME_KEY_PROP
    )
    db = c2cwsgiutils.config_utils.env_or_settings(settings, REDIS_DB_KEY, REDIS_DB_KEY_PROP)
    url = c2cwsgiutils.config_utils.env_or_settings(settings, REDIS_URL_KEY, REDIS_URL_KEY_PROP)
    redis_options_ = c2cwsgiutils.config_utils.env_or_settings(
        settings, REDIS_OPTIONS_KEY, REDIS_OPTIONS_KEY_PROP
    )

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
        _master = redis.client.Redis.from_url(url, decode_responses=True, **redis_options)
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
