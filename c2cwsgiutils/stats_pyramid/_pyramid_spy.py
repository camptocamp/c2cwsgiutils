from typing import Any, Callable, Dict, Optional

import pyramid.config
import pyramid.events
import pyramid.request
from pyramid.httpexceptions import HTTPException

from c2cwsgiutils import stats


def _add_server_metric(
    request: pyramid.request.Request,
    name: str,
    duration: Optional[float] = None,
    description: Optional[str] = None,
) -> None:
    # format: <name>;dur=<duration>;desc=<description>
    metric = name
    if duration is not None:
        metric += ";dur=" + str(round(duration * 1000))
    if description is not None:
        metric += ";desc=" + description

    if "Server-Timing" not in request.response.headers:
        request.response.headers["Server-Timing"] = metric
    else:
        request.response.headers["Server-Timing"] += ", " + metric


def _create_finished_cb(
    kind: str, measure: stats.Timer
) -> Callable[[pyramid.request.Request], None]:  # pragma: nocover
    def finished_cb(request: pyramid.request.Request) -> None:
        if request.exception is not None:
            if isinstance(request.exception, HTTPException):
                status = request.exception.code
            else:
                status = 500
        else:
            status = request.response.status_code
        if request.matched_route is None:
            name = "_not_found"
        else:
            name = request.matched_route.name
            if kind == "route":
                _add_server_metric(request, "route", description=name)
        if stats.USE_TAGS:
            key = [kind]
            tags: Optional[Dict[str, Any]] = dict(
                method=request.method, route=name, status=status, group=status // 100
            )
        else:
            key = [kind, request.method, name, status]
            tags = None
        duration = measure.stop(key, tags)
        _add_server_metric(request, kind, duration=duration)

    return finished_cb


def _request_callback(event: pyramid.events.NewRequest) -> None:  # pragma: nocover
    """
    Callback called when a new HTTP request is incoming.
    """
    measure = stats.timer()
    event.request.add_finished_callback(_create_finished_cb("route", measure))


def _before_rendered_callback(event: pyramid.events.BeforeRender) -> None:  # pragma: nocover
    """
    Callback called when the rendering is starting.
    """
    request = event.get("request", None)
    if request:
        measure = stats.timer()
        request.add_finished_callback(_create_finished_cb("render", measure))


def init(config: pyramid.config.Configurator) -> None:  # pragma: nocover
    """
    Subscribe to Pyramid events in order to get some stats on route time execution.

    :param config: The Pyramid config
    """
    config.add_subscriber(_request_callback, pyramid.events.NewRequest)
    config.add_subscriber(_before_rendered_callback, pyramid.events.BeforeRender)
