import time
from typing import Callable, Optional

import prometheus_client
import pyramid.config
import pyramid.events
import pyramid.request
from pyramid.httpexceptions import HTTPException

from c2cwsgiutils import prometheus

_PROMETHEUS_PYRAMID_ROUTES_SUMMARY = prometheus_client.Summary(
    prometheus.build_metric_name("pyramid_routes"),
    "Pyramid routes",
    ["method", "route", "status", "group"],
    unit="seconds",
)
_PROMETHEUS_PYRAMID_VIEWS_SUMMARY = prometheus_client.Summary(
    prometheus.build_metric_name("pyramid_render"),
    "Pyramid render",
    ["method", "route", "status", "group"],
    unit="seconds",
)


def _add_server_metric(
    request: pyramid.request.Request,
    name: str,
    duration: Optional[float] = None,
    description: Optional[str] = None,
) -> None:
    # format: <name>;due=<duration>;desc=<description>
    metric = name
    if duration is not None:
        metric += ";due=" + str(round(duration * 1000))
    if description is not None:
        metric += ";desc=" + description

    if "Server-Timing" not in request.response.headers:
        request.response.headers["Server-Timing"] = metric
    else:
        request.response.headers["Server-Timing"] += ", " + metric


def _create_finished_cb(
    kind: str, measure: prometheus_client.Summary
) -> Callable[[pyramid.request.Request], None]:  # pragma: nocover
    start = time.process_time()

    def finished_cb(request: pyramid.request.Request) -> None:
        if request.exception is not None:
            if isinstance(request.exception, HTTPException):
                status = request.exception.code
            else:
                status = 599
        else:
            status = request.response.status_code
        if request.matched_route is None:
            name = "_not_found"
        else:
            name = request.matched_route.name
            if kind == "route":
                _add_server_metric(request, "route", description=name)
        measure.labels(
            method=request.method, route=name, status=status, group=str(status // 100 * 100)
        ).observe(time.process_time() - start)
        _add_server_metric(request, kind, duration=time.process_time() - start)

    return finished_cb


def _request_callback(event: pyramid.events.NewRequest) -> None:  # pragma: nocover
    """Finish the callback called when a new HTTP request is incoming."""
    event.request.add_finished_callback(_create_finished_cb("route", _PROMETHEUS_PYRAMID_ROUTES_SUMMARY))


def _before_rendered_callback(event: pyramid.events.BeforeRender) -> None:  # pragma: nocover
    """Finish the callback called when the rendering is starting."""
    request = event.get("request", None)
    if request:
        request.add_finished_callback(_create_finished_cb("render", _PROMETHEUS_PYRAMID_VIEWS_SUMMARY))


def init(config: pyramid.config.Configurator) -> None:  # pragma: nocover
    """
    Subscribe to Pyramid events in order to get some stats on route time execution.

    Arguments:

        config: The Pyramid config
    """
    config.add_subscriber(_request_callback, pyramid.events.NewRequest)
    config.add_subscriber(_before_rendered_callback, pyramid.events.BeforeRender)
