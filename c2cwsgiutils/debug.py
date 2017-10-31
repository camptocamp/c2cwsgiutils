import logging
import objgraph
import pyramid.config
import pyramid.request
import pyramid.response
import threading
import time
import traceback
from typing import Dict, Mapping, List, Any
import sys

from c2cwsgiutils import _utils, _auth, _broadcast

CONFIG_KEY = 'c2c.debug_view_secret'
ENV_KEY = 'DEBUG_VIEW_SECRET'

LOG = logging.getLogger(__name__)


def _dump_stacks(request: pyramid.request.Request) -> List[Mapping[str, List[Mapping[str, Any]]]]:
    _auth.auth_view(request, ENV_KEY, CONFIG_KEY)
    result = _broadcast.broadcast('c2c_dump_stacks', expect_answers=True)
    assert result is not None
    return result


def _dump_stacks_impl() -> Dict[str, List[Dict[str, Any]]]:
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    threads = {}
    for threadId, stack in sys._current_frames().items():  # pylint: disable=W0212
        frames = []
        for filename, lineno, name, line in traceback.extract_stack(stack):  # type: ignore
            cur = {
                'file': filename,
                'line': lineno,
                'function': name
            }
            if line:
                cur['code'] = line.strip()
            frames.append(cur)
        threads["%s(%d)" % (id2name.get(threadId, ""), threadId)] = frames
    return threads


def _dump_memory(request: pyramid.request.Request) -> List[Mapping[str, Any]]:
    _auth.auth_view(request, ENV_KEY, CONFIG_KEY)
    limit = int(request.params.get('limit', '30'))
    result = _broadcast.broadcast('c2c_dump_memory', params={'limit': limit}, expect_answers=True)
    assert result is not None
    return result


def _dump_memory_impl(limit: int) -> Mapping[str, Any]:
    nb_collected = objgraph.gc.collect()
    return {
        'nb_collected': nb_collected,
        'most_common_types': objgraph.most_common_types(limit=limit, shortnames=False),
        'leaking_objects': objgraph.most_common_types(limit=limit, shortnames=False,
                                                      objects=objgraph.get_leaking_objects())
    }


def _sleep(request: pyramid.request.Request) -> pyramid.response.Response:
    _auth.auth_view(request, ENV_KEY, CONFIG_KEY)
    timeout = float(request.params['time'])
    time.sleep(timeout)
    request.response.status_code = 204
    return request.response


def _headers(request: pyramid.request.Request) -> Mapping[str, str]:
    _auth.auth_view(request, ENV_KEY, CONFIG_KEY)
    return dict(request.headers)


def init(config: pyramid.config.Configurator) -> None:
    if _utils.env_or_config(config, ENV_KEY, CONFIG_KEY, False):
        _broadcast.subscribe('c2c_dump_memory', _dump_memory_impl)
        _broadcast.subscribe('c2c_dump_stacks', _dump_stacks_impl)

        config.add_route("c2c_debug_stacks", _utils.get_base_path(config) + r"/debug/stacks",
                         request_method="GET")
        config.add_view(_dump_stacks, route_name="c2c_debug_stacks", renderer="json", http_cache=0)

        config.add_route("c2c_debug_memory", _utils.get_base_path(config) + r"/debug/memory",
                         request_method="GET")
        config.add_view(_dump_memory, route_name="c2c_debug_memory", renderer="json", http_cache=0)

        config.add_route("c2c_debug_sleep", _utils.get_base_path(config) + r"/debug/sleep",
                         request_method="GET")
        config.add_view(_sleep, route_name="c2c_debug_sleep", renderer="json", http_cache=0)

        config.add_route("c2c_debug_headers", _utils.get_base_path(config) + r"/debug/headers",
                         request_method="GET")
        config.add_view(_headers, route_name="c2c_debug_headers", renderer="json", http_cache=0)

        LOG.info("Enabled the /debug/stacks API")
