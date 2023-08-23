import gc
import logging
import re
import time
from collections.abc import Mapping
from datetime import datetime
from io import StringIO
from typing import Any, Callable, cast

import objgraph
import pyramid.config
import pyramid.request
import pyramid.response
from pyramid.httpexceptions import HTTPException, exception_response

from c2cwsgiutils import auth, broadcast, config_utils
from c2cwsgiutils.debug.utils import dump_memory_maps, get_size

LOG = logging.getLogger(__name__)
SPACE_RE = re.compile(r" +")


def _beautify_stacks(source: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Group the identical stacks together along with a list of threads sporting them."""
    results: list[Mapping[str, Any]] = []
    for host_stacks in source:
        host_id = f"{host_stacks['hostname']}/{host_stacks['pid']:d}"
        for thread, frames in host_stacks["threads"].items():
            full_id = host_id + "/" + thread
            for existing in results:
                if existing["frames"] == frames:
                    existing["threads"].append(full_id)
                    break
            else:
                results.append({"frames": frames, "threads": [full_id]})
    return results


def _dump_stacks(request: pyramid.request.Request) -> list[Mapping[str, Any]]:
    auth.auth_view(request)
    result = broadcast.broadcast("c2c_dump_stacks", expect_answers=True)
    assert result is not None
    return _beautify_stacks(result)


def _dump_memory(request: pyramid.request.Request) -> list[Mapping[str, Any]]:
    auth.auth_view(request)
    limit = int(request.params.get("limit", "30"))
    analyze_type = request.params.get("analyze_type")
    python_internals_map = request.params.get("python_internals_map", "0").lower() in ("", "1", "true", "on")
    result = broadcast.broadcast(
        "c2c_dump_memory",
        params={"limit": limit, "analyze_type": analyze_type, "python_internals_map": python_internals_map},
        expect_answers=True,
        timeout=70,
    )
    assert result is not None
    return result


def _dump_memory_diff(request: pyramid.request.Request) -> list[Any]:
    auth.auth_view(request)
    limit = int(request.params.get("limit", "30"))
    if "path" in request.matchdict:
        # deprecated
        path = "/" + "/".join(request.matchdict["path"])
    else:
        path = request.params["path"]

    sub_request = request.copy()
    split_path = path.split("?")
    sub_request.path_info = split_path[0]
    if len(split_path) > 1:
        sub_request.query_string = split_path[1]

    # warm-up run
    try:
        if "no_warmup" not in request.params:
            request.invoke_subrequest(sub_request)
    except Exception:  # nosec  # pylint: disable=broad-except
        pass

    LOG.debug("checking memory growth for %s", path)

    peak_stats: dict[Any, Any] = {}
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

    return objgraph.growth(limit=limit, peak_stats=peak_stats, shortnames=False)  # type: ignore


def _sleep(request: pyramid.request.Request) -> pyramid.response.Response:
    auth.auth_view(request)
    timeout = float(request.params["time"])
    time.sleep(timeout)
    request.response.status_code = 204
    return request.response


def _headers(request: pyramid.request.Request) -> Mapping[str, Any]:
    auth.auth_view(request)
    result = {
        "headers": dict(request.headers),
        "client_info": {
            "client_addr": request.client_addr,
            "host": request.host,
            "host_port": request.host_port,
            "http_version": request.http_version,
            "path": request.path,
            "path_info": request.path_info,
            "remote_addr": request.remote_addr,
            "remote_host": request.remote_host,
            "scheme": request.scheme,
            "server_name": request.server_name,
            "server_port": request.server_port,
        },
    }
    if "status" in request.params:
        raise exception_response(int(request.params["status"]), detail=result)
    else:
        return result


def _error(request: pyramid.request.Request) -> Any:
    auth.auth_view(request)
    raise exception_response(int(request.params["status"]), detail="Test")


def _time(request: pyramid.request.Request) -> Any:
    return {
        "local_time": str(datetime.now()),
        "gmt_time": str(datetime.utcnow()),
        "epoch": time.time(),
        "timezone": datetime.now().astimezone().tzname(),
    }


def _add_view(
    config: pyramid.config.Configurator, name: str, path: str, view: Callable[[pyramid.request.Request], Any]
) -> None:
    config.add_route(
        "c2c_debug_" + name, config_utils.get_base_path(config) + r"/debug/" + path, request_method="GET"
    )
    config.add_view(view, route_name="c2c_debug_" + name, renderer="fast_json", http_cache=0)


def _dump_memory_maps(request: pyramid.request.Request) -> list[dict[str, Any]]:
    auth.auth_view(request)
    return sorted(dump_memory_maps(), key=lambda i: cast(int, -i.get("pss_kb", 0)))


def _show_refs(request: pyramid.request.Request) -> pyramid.response.Response:
    auth.auth_view(request)
    for generation in range(3):
        gc.collect(generation)

    objs: list[Any] = []
    if "analyze_type" in request.params:
        objs = objgraph.by_type(request.params["analyze_type"])
    elif "analyze_id" in request.params:
        objs = [objgraph.by(int(request.params["analyze_id"]))]

    args: dict[str, Any] = {
        "refcounts": True,
    }
    if request.params.get("max_depth", "") != "":
        args["max_depth"] = int(request.params["max_depth"])
    if request.params.get("too_many", "") != "":
        args["too_many"] = int(request.params["too_many"])
    if request.params.get("min_size_kb", "") != "":
        args["filter"] = lambda obj: get_size(obj) > (int(request.params["min_size_kb"]) * 1024)
    if request.params.get("no_extra_info", "") == "":
        args["extra_info"] = lambda obj: f"{get_size(obj) / 1024:.3f} kb\n{id(obj)}"

    result = StringIO()
    if request.params.get("backrefs", "") != "":
        objgraph.show_backrefs(objs, output=result, **args)
    else:
        objgraph.show_refs(objs, output=result, filter=lambda x: not objgraph.inspect.isclass(x), **args)

    request.response.content_type = "text/vnd.graphviz"
    request.response.text = result.getvalue()
    result.close()
    return request.response


def init(config: pyramid.config.Configurator) -> None:
    """Initialize all the development view."""
    _add_view(config, "stacks", "stacks", _dump_stacks)
    _add_view(config, "memory", "memory", _dump_memory)
    _add_view(config, "memory_diff", "memory_diff", _dump_memory_diff)
    _add_view(config, "memory_maps", "memory_maps", _dump_memory_maps)
    _add_view(config, "memory_diff_deprecated", "memory_diff/*path", _dump_memory_diff)
    _add_view(config, "sleep", "sleep", _sleep)
    _add_view(config, "headers", "headers", _headers)
    _add_view(config, "error", "error", _error)
    _add_view(config, "time", "time", _time)
    _add_view(config, "show_refs", "show_refs.dot", _show_refs)
    LOG.info("Enabled the /debug/... API")
