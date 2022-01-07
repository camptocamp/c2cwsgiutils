import logging
import warnings
from typing import Any, Callable, Dict, Optional  # noqa  # pylint: disable=unused-import

import pyramid.config

from c2cwsgiutils import config_utils, stats

LOG = logging.getLogger(__name__)
ORIG: Optional[Callable[..., Any]] = None


def _execute_command_patch(self: Any, *args: Any, **options: Any) -> Any:
    if stats.USE_TAGS:
        key = ["redis"]
        tags: Optional[Dict[str, str]] = dict(cmd=args[0])
    else:
        key = ["redis", args[0]]
        tags = None
    assert ORIG is not None
    with stats.outcome_timer_context(key, tags):
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
