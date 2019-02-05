import logging
from typing import Optional, Callable, Any, Dict  # noqa  # pylint: disable=unused-import

import pyramid.config

from c2cwsgiutils import stats, _utils

LOG = logging.getLogger(__name__)
ORIG: Optional[Callable] = None


def _execute_command_patch(self: Any, *args: Any, **options: Any) -> Any:
    if stats.USE_TAGS:
        key = ['redis']
        tags: Optional[Dict] = dict(cmd=args[0])
    else:
        key = ['redis', args[0]]
        tags = None
    if ORIG is not None:
        with stats.outcome_timer_context(key, tags):
            return ORIG(self, *args, **options)


def init(config: Optional[pyramid.config.Configurator] = None) -> None:
    global ORIG
    if _utils.env_or_config(config, 'C2C_TRACK_REDIS', 'c2c.track_redis', True, _utils.config_bool):
        try:
            import redis.client
            ORIG = redis.client.StrictRedis.execute_command
            redis.client.StrictRedis.execute_command = _execute_command_patch
            LOG.info("Enabled the redis tracking")
        except Exception:  # pragma: nocover
            LOG.warning("Cannot enable redis tracking", exc_info=True)
