from typing import Any

import pyramid.config
import ujson
from pyramid.renderers import JSON


def fast_dumps(v: Any, **_kargv: Any) -> str:
    return ujson.dumps(v, ensure_ascii=False, indent=2, sort_keys=True, escape_forward_slashes=False)


def init(config: pyramid.config.Configurator) -> None:
    config.add_renderer("json", JSON(indent=2, sort_keys=True))
    config.add_renderer("fast_json", JSON(serializer=fast_dumps))
