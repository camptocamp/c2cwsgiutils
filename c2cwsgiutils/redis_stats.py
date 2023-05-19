import logging
import warnings
from typing import Any, Callable, Optional

import pyramid.config

from c2cwsgiutils import config_utils, metrics_stats, stats

LOG = logging.getLogger(__name__)
ORIG: Optional[Callable[..., Any]] = None

_COUNTER = metrics_stats.CounterStatus(
    "redis", "Number of redis commands", ["redis"], ["{command}"], {"command": "cmd"}
)


def _execute_command_patch(self: Any, *args: Any, **options: Any) -> Any:
    assert ORIG is not None
    with _COUNTER.outcome_timer_context(key, tags):
        return ORIG(self, *args, **options)


def init(config: Optional[pyramid.config.Configurator] = None) -> None:
    """Initialize the Redis tracking, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: Optional[pyramid.config.Configurator] = None) -> None:
    """Initialize the Redis tracking."""
    global ORIG
    if config_utils.env_or_config(
        config, "C2C_TRACK_REDIS", "c2c.track_redis", True, config_utils.config_bool
    ):
        try:
            import redis.client

            ORIG = redis.client.Redis.execute_command
            redis.client.Redis.execute_command = _execute_command_patch  # type: ignore
            LOG.info("Enabled the redis tracking")
        except Exception:  # pragma: nocover  # pylint: disable=broad-except
            LOG.warning("Cannot enable redis tracking", exc_info=True)
