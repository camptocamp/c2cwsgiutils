import logging
import warnings
from collections.abc import Mapping
from typing import Any, cast

import pyramid.request

from c2cwsgiutils import auth, broadcast, config_utils, db, redis_utils

_LOG = logging.getLogger(__name__)
_CONFIG_KEY = "c2c.db_maintenance_view_enabled"
_ENV_KEY = "C2C_DB_MAINTENANCE_VIEW_ENABLED"
_REDIS_PREFIX = "c2c_db_maintenance_"


def install_subscriber(config: pyramid.config.Configurator) -> None:
    """Install the view to configure the loggers, if configured to do so, for backward compatibility."""
    warnings.warn("install_subscriber function is deprecated; use includeme instead", stacklevel=2)
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """Install the view to configure the loggers, if configured to do so."""
    if auth.is_enabled(config, _ENV_KEY, _CONFIG_KEY):
        config.add_route(
            "c2c_db_maintenance",
            config_utils.get_base_path(config) + r"/db/maintenance",
            request_method="GET",
        )
        config.add_view(_db_maintenance, route_name="c2c_db_maintenance", renderer="fast_json", http_cache=0)
        _restore(config)
        _LOG.info("Enabled the /db/maintenance API")


def _db_maintenance(request: pyramid.request.Request) -> Mapping[str, Any]:
    auth.auth_view(request)
    readonly_param = cast("str", request.params.get("readonly"))
    if readonly_param is not None:
        readonly = readonly_param.lower() == "true"

        _LOG.critical("Readonly DB status changed from %s to %s", db.FORCE_READONLY, readonly)
        _set_readonly(value=readonly)
        _store(request.registry.settings, readonly)
        return {"status": 200, "readonly": readonly}
    readonly = _get_redis_value(request.registry.settings)
    if readonly is not None:
        readonly = readonly == "true"
    return {"status": 200, "current_readonly": readonly}


@broadcast.decorator(expect_answers=True)
def _set_readonly(value: bool) -> bool:
    db.FORCE_READONLY = value
    return True


def _restore(config: pyramid.config.Configurator) -> None:
    try:
        readonly = _get_redis_value(config.get_settings())
        if readonly is not None:
            _LOG.debug("Restoring readonly DB status to %s", readonly)
            db.FORCE_READONLY = readonly == "true"
    except ImportError:
        pass  # don't have redis
    except Exception:  # pylint: disable=broad-exception-caught
        # survive an error since crashing now can have bad consequences for the service. :/
        _LOG.error("Cannot restore readonly DB status.", exc_info=True)


def _store(settings: Mapping[str, Any], readonly: bool) -> None:
    master, _, _ = redis_utils.get(settings)
    if master is not None:
        master.set(_REDIS_PREFIX + "force_readonly", "true" if readonly else "false")


def _get_redis_value(settings: Mapping[str, Any]) -> str | None:
    _, slave, _ = redis_utils.get(settings)
    if slave is not None:
        value = slave.get(_REDIS_PREFIX + "force_readonly")
        return str(value) if value else None
    return None
