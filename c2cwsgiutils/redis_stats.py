import logging
import pyramid.config
from typing import Optional, Callable, Any  # noqa  # pylint: disable=unused-import

from c2cwsgiutils import stats, _utils

LOG = logging.getLogger(__name__)
ORIG = None  # type: Optional[Callable]


def _execute_command_patch(self: Any, *args: Any, **options: Any) -> Any:
    with stats.timer_context(['redis', args[0]]):
        return ORIG(self, *args, **options)  # type: ignore


def init(config: Optional[pyramid.config.Configurator]=None) -> None:
    global ORIG
    if _utils.env_or_config(config, 'C2C_TRACK_REDIS', 'c2c.track_redis', True, _utils.config_bool):
        try:
            import redis.client
            ORIG = redis.client.StrictRedis.execute_command
            redis.client.StrictRedis.execute_command = _execute_command_patch
            LOG.info("Enabled the redis tracking")
        except Exception:  # pragma: nocover
            LOG.warning("Cannot enable redis tracking", exc_info=True)
