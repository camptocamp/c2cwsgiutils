import logging
import warnings
from collections.abc import Callable
from typing import Any

import prometheus_client
import pyramid.config

from c2cwsgiutils import config_utils, prometheus

_LOG = logging.getLogger(__name__)
_ORIG: Callable[..., Any] | None = None

_PROMETHEUS_REDIS_SUMMARY = prometheus_client.Summary(
    prometheus.build_metric_name("redis"),
    "Number of redis commands",
    ["command"],
    unit="seconds",
)


def _execute_command_patch(self: Any, command: str, *args: Any, **options: Any) -> Any:
    assert _ORIG is not None
    with _PROMETHEUS_REDIS_SUMMARY.labels(command=command).time():
        return _ORIG(self, command, *args, **options)


def init(config: pyramid.config.Configurator | None = None) -> None:
    """Initialize the Redis tracking, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead", stacklevel=2)
    includeme(config)


def includeme(config: pyramid.config.Configurator | None = None) -> None:
    """Initialize the Redis tracking."""
    global _ORIG  # pylint: disable=global-statement
    if config_utils.env_or_config(
        config,
        "C2C_TRACK_REDIS",
        "c2c.track_redis",
        default=True,
        type_=config_utils.config_bool,
    ):
        try:
            import redis.client  # pylint: disable=import-outside-toplevel

            _ORIG = redis.client.Redis.execute_command
            redis.client.Redis.execute_command = _execute_command_patch  # type: ignore[method-assign,assignment]
            _LOG.info("Enabled the redis tracking")
        except Exception:  # pragma: nocover  # pylint: disable=broad-exception-caught
            _LOG.warning("Cannot enable redis tracking", exc_info=True)
