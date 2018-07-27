import gc
import logging
import objgraph
import pyramid.config
from pyramid.httpexceptions import HTTPException, exception_response
import pyramid.request
import pyramid.response
import threading
import time
import traceback
from typing import Dict, Mapping, List, Any, Callable
import sys

from c2cwsgiutils import _utils, _auth, broadcast

DEPRECATED_CONFIG_KEY = 'c2c.debug_view_secret'
DEPRECATED_ENV_KEY = 'DEBUG_VIEW_SECRET'
CONFIG_KEY = 'c2c.debug_view_enabled'
ENV_KEY = 'C2C_DEBUG_VIEW_ENABLED'

LOG = logging.getLogger(__name__)


def _dump_stacks(request: pyramid.request.Request) -> List[Mapping[str, List[Mapping[str, Any]]]]:
    _auth.auth_view(request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY)
    result = broadcast.broadcast('c2c_dump_stacks', expect_answers=True)
    assert result is not None
    return result


def _dump_stacks_impl() -> Dict[str, List[Dict[str, Any]]]:
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    threads = {}
    for thread_id, stack in sys._current_frames().items():  # pylint: disable=W0212
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
        threads["%s(%d)" % (id2name.get(thread_id, ""), thread_id)] = frames
    return threads


def _dump_memory(request: pyramid.request.Request) -> List[Mapping[str, Any]]:
    _auth.auth_view(request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY)
    limit = int(request.params.get('limit', '30'))
    result = broadcast.broadcast('c2c_dump_memory', params={'limit': limit}, expect_answers=True)
    assert result is not None
    return result


def _dump_memory_diff(request: pyramid.request.Request) -> List:
    _auth.auth_view(request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY)
    limit = int(request.params.get('limit', '30'))
    if 'path' in request.matchdict:
        # deprecated
        path = '/' + '/'.join(request.matchdict['path'])
    else:
        path = request.params['path']

    sub_request = request.copy()
    split_path = path.split('?')
    sub_request.path_info = split_path[0]
    if len(split_path) > 1:
        sub_request.query_string = split_path[1]

    # warmup run
    try:
        request.invoke_subrequest(sub_request)
    except Exception:  # nosec
        pass

    LOG.debug("checking memory growth for %s", path)

    peak_stats = {}  # type: Dict
    for i in range(3):
        gc.collect(i)

    objgraph.growth(limit=limit, peak_stats=peak_stats, shortnames=False)

    response = None
    try:
        response = request.invoke_subrequest(sub_request)
        LOG.debug("response was %d", response.status_code)

    except HTTPException as ex:
        LOG.debug("response was %s", str(ex))

    del response

    for i in range(3):
        gc.collect(i)

    growth = objgraph.growth(limit=limit, peak_stats=peak_stats, shortnames=False)

    return growth


def _dump_memory_impl(limit: int) -> Mapping[str, Any]:
    nb_collected = [gc.collect(generation) for generation in range(3)]
    return {
        'nb_collected': nb_collected,
        'most_common_types': objgraph.most_common_types(limit=limit, shortnames=False),
        'leaking_objects': objgraph.most_common_types(limit=limit, shortnames=False,
                                                      objects=objgraph.get_leaking_objects())
    }


def _sleep(request: pyramid.request.Request) -> pyramid.response.Response:
    _auth.auth_view(request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY)
    timeout = float(request.params['time'])
    time.sleep(timeout)
    request.response.status_code = 204
    return request.response


def _headers(request: pyramid.request.Request) -> Mapping[str, str]:
    _auth.auth_view(request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY)
    return dict(request.headers)


def _error(request: pyramid.request.Request) -> Any:
    _auth.auth_view(request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY)
    raise exception_response(int(request.params['status']), detail="Test")


def _add_view(config: pyramid.config.Configurator, name: str, path: str, view: Callable) -> None:
    config.add_route("c2c_debug_" + name, _utils.get_base_path(config) + r"/debug/" + path,
                     request_method="GET")
    config.add_view(view, route_name="c2c_debug_" + name, renderer="fast_json", http_cache=0)


def init(config: pyramid.config.Configurator) -> None:
    if _utils.env_or_config(config, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY, False) or \
            _auth.is_enabled(config, ENV_KEY, CONFIG_KEY):
        broadcast.subscribe('c2c_dump_memory', _dump_memory_impl)
        broadcast.subscribe('c2c_dump_stacks', _dump_stacks_impl)

        _add_view(config, "stacks", "stacks", _dump_stacks)
        _add_view(config, "memory", "memory", _dump_memory)
        _add_view(config, "memory_diff", "memory_diff", _dump_memory_diff)
        _add_view(config, "memory_diff_deprecated", "memory_diff/*path", _dump_memory_diff)
        _add_view(config, "sleep", "sleep", _sleep)
        _add_view(config, "headers", "headers", _headers)
        _add_view(config, "error", "error", _error)

        LOG.info("Enabled the /debug/... API")
