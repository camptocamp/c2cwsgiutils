"""Broadcast messages to all the processes of Gunicorn in every containers."""
import functools
import logging
import warnings
from typing import Any, Callable, Optional, TypeVar

import pyramid.config

from c2cwsgiutils import config_utils, redis_utils
from c2cwsgiutils.broadcast import interface, local, redis

LOG = logging.getLogger(__name__)
BROADCAST_ENV_KEY = "C2C_BROADCAST_PREFIX"
BROADCAST_CONFIG_KEY = "c2c.broadcast_prefix"

_broadcaster: Optional[interface.BaseBroadcaster] = None


def init(config: Optional[pyramid.config.Configurator] = None) -> None:
    """Initialize the broadcaster with Redis, if configured, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: Optional[pyramid.config.Configurator] = None) -> None:
    """
    Initialize the broadcaster with Redis, if configured.

    Otherwise, fall back to a fake local implementation.
    """
    global _broadcaster
    broadcast_prefix = config_utils.env_or_config(
        config, BROADCAST_ENV_KEY, BROADCAST_CONFIG_KEY, "broadcast_api_"
    )
    master, slave, _ = redis_utils.get(config.get_settings() if config else None)
    if _broadcaster is None:
        if master is not None and slave is not None:
            _broadcaster = redis.RedisBroadcaster(broadcast_prefix, master, slave)
            LOG.info("Broadcast service setup using Redis implementation")
        else:
            _broadcaster = local.LocalBroadcaster()
            LOG.info("Broadcast service setup using local implementation")
    elif isinstance(_broadcaster, local.LocalBroadcaster) and master is not None and slave is not None:
        LOG.info("Switching from a local broadcaster to a Redis broadcaster")
        prev_broadcaster = _broadcaster
        _broadcaster = redis.RedisBroadcaster(broadcast_prefix, master, slave)
        _broadcaster.copy_local_subscriptions(prev_broadcaster)


def _get(need_init: bool = False) -> interface.BaseBroadcaster:
    global _broadcaster
    if _broadcaster is None:
        if need_init:
            LOG.error("Broadcast functionality used before it is setup")
        _broadcaster = local.LocalBroadcaster()
    return _broadcaster


def cleanup() -> None:
    """Cleanup the broadcaster to force to reinitialize it."""

    global _broadcaster
    _broadcaster = None


def subscribe(channel: str, callback: Callable[..., Any]) -> None:
    """
    Subscribe to a broadcast channel with the given callback.

    The callback will be called with its parameters
    taken from the dict provided in the _broadcaster.broadcast "params" parameter.

    A channel can be subscribed only once.
    """
    _get().subscribe(channel, callback)


def unsubscribe(channel: str) -> None:
    """Unsubscribe from a channel."""
    _get().unsubscribe(channel)


def broadcast(
    channel: str, params: Optional[dict[str, Any]] = None, expect_answers: bool = False, timeout: float = 10
) -> Optional[list[Any]]:
    """
    Broadcast a message to the given channel.

    If answers are expected, it will wait up to "timeout" seconds to get all the answers.
    """
    return _get(need_init=True).broadcast(
        channel, params if params is not None else {}, expect_answers, timeout
    )


# We can also templatise the argument with Python 3.10
# See: https://www.python.org/dev/peps/pep-0612/
_DECORATOR_RETURN = TypeVar("_DECORATOR_RETURN")


def decorator(
    channel: Optional[str] = None, expect_answers: bool = False, timeout: float = 10
) -> Callable[[Callable[..., _DECORATOR_RETURN]], Callable[..., Optional[list[_DECORATOR_RETURN]]]]:
    """
    Decorate function will be called through the broadcast functionality.

    If expect_answers is set to True, the returned value will be a list of all the answers.
    """

    def impl(func: Callable[..., _DECORATOR_RETURN]) -> Callable[..., Optional[list[_DECORATOR_RETURN]]]:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Optional[list[_DECORATOR_RETURN]]:
            return broadcast(_channel, params=kwargs, expect_answers=expect_answers, timeout=timeout)

        if channel is None:
            _channel = f"c2c_decorated_{func.__module__}.{func.__name__}"
        else:
            _channel = channel
        subscribe(_channel, func)

        return wrapper

    return impl
