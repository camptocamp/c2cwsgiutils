import pyramid.config
from pyramid.renderers import JSON
from typing import Any
import ujson


def fast_dumps(v: Any, **_kargv: Any) -> str:
    return ujson.dumps(v, ensure_ascii=False, indent=2, sort_keys=True, escape_forward_slashes=False)


def init(config: pyramid.config.Configurator) -> None:
    config.add_renderer('json', JSON(indent=2, sort_keys=True))
    config.add_renderer('fast_json', JSON(serializer=fast_dumps))
