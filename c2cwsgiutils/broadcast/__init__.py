"""
Broadcast messages to all the processes of Gunicorn in every containers.
"""
import functools
import logging
import pyramid.config
from typing import Optional, Callable, Any

from c2cwsgiutils import _utils
from c2cwsgiutils.broadcast import redis, local
from c2cwsgiutils.broadcast import interface  # noqa  # pylint: disable=unused-import

LOG = logging.getLogger(__name__)
REDIS_ENV_KEY = "C2C_REDIS_URL"
REDIS_CONFIG_KEY = "c2c.redis_url"
BROADCAST_ENV_KEY = "C2C_BROADCAST_PREFIX"
BROADCAST_CONFIG_KEY = "c2c.broadcast_prefix"

_broadcaster = None  # type: Optional[interface.BaseBroadcaster]


def init(config: pyramid.config.Configurator) -> None:
    """
    Initialize the broacaster with Redis, if configured. Otherwise, fall back to a fake local implementation.
    """
    global _broadcaster
    if _broadcaster is None:
        redis_url = _utils.env_or_config(config, REDIS_ENV_KEY, REDIS_CONFIG_KEY, None)
        if redis_url is not None:
            broadcast_prefix = _utils.env_or_config(config, BROADCAST_ENV_KEY, BROADCAST_CONFIG_KEY,
                                                    "broadcast_api_")
            try:
                _broadcaster = redis.RedisBroadcaster(redis_url, broadcast_prefix)
                LOG.info("Broadcast service setup using redis: %s", redis_url)
                return
            except ImportError:  # pragma: no cover
                LOG.warning("Cannot import redis for setting up broadcast capabilities")
        _broadcaster = local.LocalBroadcaster()
        LOG.info("Broadcast service setup using local implementation")


def subscribe(channel: str, callback: Callable) -> None:
    """
    Subscribe to a broadcast channel with the given callback. The callback will be called with its parameters
    taken from the dict provided in the _broadcaster.broadcast "params" parameter.

    A channel can be subscribed only once.
    """
    global _broadcaster
    assert _broadcaster is not None
    _broadcaster.subscribe(channel, callback)


def unsubscribe(channel: str) -> None:
    """
    Unsubscribe from a channel.
    """
    global _broadcaster
    assert _broadcaster is not None
    _broadcaster.unsubscribe(channel)


def broadcast(channel: str, params: Optional[dict]=None, expect_answers: bool=False,
              timeout: float=10) -> Optional[list]:
    """
    Broadcast a message to the given channel. If answers are expected, it will wait up to "timeout" seconds
    to get all the answers.
    """
    global _broadcaster
    assert _broadcaster is not None
    return _broadcaster.broadcast(channel, params if params is not None else {}, expect_answers, timeout)


def decorator(channel: Optional[str]=None, expect_answers: bool=False, timeout: float=10) -> Callable:
    """
    The decorated function will be called through the broadcast functionality. If expect_answers is set to
    True, the returned value will be a list of all the answers.

    This works only if the module using this decorator is imported after the broadcast system is setup.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            return broadcast(_channel, params=kwargs, expect_answers=expect_answers, timeout=timeout)

        if channel is None:
            _channel = 'c2c_decorated_%s.%s' % (func.__module__, func.__name__)
        else:
            _channel = channel
        subscribe(_channel, func)

        return wrapper
    return decorator
