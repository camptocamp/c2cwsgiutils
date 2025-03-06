"""Broadcast messages to all the processes of Gunicorn in every containers."""

import functools
import logging
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

import pyramid.config

from c2cwsgiutils import config_utils, redis_utils
from c2cwsgiutils.broadcast import interface, local, redis

_LOG = logging.getLogger(__name__)
_BROADCAST_ENV_KEY = "C2C_BROADCAST_PREFIX"
_BROADCAST_CONFIG_KEY = "c2c.broadcast_prefix"

_broadcaster: interface.BaseBroadcaster | None = None


def init(config: pyramid.config.Configurator | None = None) -> None:
    """Initialize the broadcaster with Redis, if configured, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead", stacklevel=2)
    includeme(config)


def includeme(config: pyramid.config.Configurator | None = None) -> None:
    """
    Initialize the broadcaster with Redis, if configured.

    Otherwise, fall back to a fake local implementation.
    """
    global _broadcaster  # pylint: disable=global-statement
    broadcast_prefix = config_utils.env_or_config(
        config,
        _BROADCAST_ENV_KEY,
        _BROADCAST_CONFIG_KEY,
        "broadcast_api_",
    )
    master, slave, _ = redis_utils.get(config.get_settings() if config else None)
    if _broadcaster is None:
        if master is not None and slave is not None:
            _broadcaster = redis.RedisBroadcaster(broadcast_prefix, master, slave)
            _LOG.info("Broadcast service setup using Redis implementation")
        else:
            _broadcaster = local.LocalBroadcaster()
            _LOG.info("Broadcast service setup using local implementation")
    elif isinstance(_broadcaster, local.LocalBroadcaster) and master is not None and slave is not None:
        _LOG.info("Switching from a local broadcaster to a Redis broadcaster")
        prev_broadcaster = _broadcaster
        _broadcaster = redis.RedisBroadcaster(broadcast_prefix, master, slave)
        _broadcaster.copy_local_subscriptions(prev_broadcaster)


def _get(need_init: bool = False) -> interface.BaseBroadcaster:
    global _broadcaster  # pylint: disable=global-statement
    if _broadcaster is None:
        if need_init:
            _LOG.error("Broadcast functionality used before it is setup")
        _broadcaster = local.LocalBroadcaster()
    return _broadcaster


def cleanup() -> None:
    """Cleanup the broadcaster to force to reinitialize it."""
    global _broadcaster  # pylint: disable=global-statement
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
    channel: str,
    params: dict[str, Any] | None = None,
    expect_answers: bool = False,
    timeout: float = 10,
) -> list[Any] | None:
    """
    Broadcast a message to the given channel.

    If answers are expected, it will wait up to "timeout" seconds to get all the answers.
    """
    return _get(need_init=True).broadcast(
        channel,
        params if params is not None else {},
        expect_answers,
        timeout,
    )


# We can also templatise the argument with Python 3.10
# See: https://www.python.org/dev/peps/pep-0612/
_DecoratorReturn = TypeVar("_DecoratorReturn")


def decorator(
    channel: str | None = None,
    expect_answers: bool = False,
    timeout: float = 10,
) -> Callable[[Callable[..., _DecoratorReturn]], Callable[..., list[_DecoratorReturn] | None]]:
    """
    Decorate function will be called through the broadcast functionality.

    If expect_answers is set to True, the returned value will be a list of all the answers.
    """

    def impl(func: Callable[..., _DecoratorReturn]) -> Callable[..., list[_DecoratorReturn] | None]:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> list[_DecoratorReturn] | None:
            return broadcast(_channel, params=kwargs, expect_answers=expect_answers, timeout=timeout)

        _channel = f"c2c_decorated_{func.__module__}.{func.__name__}" if channel is None else channel
        subscribe(_channel, func)

        return wrapper

    return impl
