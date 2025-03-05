import warnings
from typing import Any

import pyramid.config
import ujson
from cornice.renderer import CorniceRenderer
from pyramid.renderers import JSON

from c2cwsgiutils.config_utils import config_bool, env_or_config


class _FastDumps:
    """Dump the json fast using ujson."""

    def __init__(self, pretty_print: bool, sort_keys: bool) -> None:
        self.pretty_print = pretty_print
        self.sort_keys = sort_keys

    def __call__(self, v: Any, **_kargv: Any) -> str:
        return ujson.dumps(
            v,
            ensure_ascii=False,
            indent=2 if self.pretty_print else 0,
            sort_keys=self.sort_keys,
            escape_forward_slashes=False,
        )


def init(config: pyramid.config.Configurator) -> None:
    """Initialize json and fast_json renderer, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead", stacklevel=2)
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """Initialize json and fast_json renderer."""
    pretty_print = config_bool(
        env_or_config(config, "C2C_JSON_PRETTY_PRINT", "c2c.json.pretty_print", "false"),
    )
    sort_keys = config_bool(env_or_config(config, "C2C_JSON_SORT_KEYS", "c2c.json.sort_keys", "false"))

    fast_dump = _FastDumps(pretty_print, sort_keys)

    config.add_renderer("json", JSON(indent=2 if pretty_print else None, sort_keys=sort_keys))
    config.add_renderer("fast_json", JSON(serializer=fast_dump))
    config.add_renderer(
        "cornice_json",
        CorniceRenderer(indent=2 if pretty_print else None, sort_keys=sort_keys),
    )
    config.add_renderer("cornice_fast_json", CorniceRenderer(serializer=fast_dump))
