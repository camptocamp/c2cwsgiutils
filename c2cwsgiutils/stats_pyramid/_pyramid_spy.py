import time
from typing import Callable, Optional

import pyramid.config
import pyramid.events
import pyramid.request
from pyramid.httpexceptions import HTTPException

from c2cwsgiutils import _metrics_stats, metrics, stats

_COUNTER_ROUTES = _metrics_stats.Counter(
    "routes",
    "Pyramid routes",
    ["routes", "counter"],
    ["routes", "timer"],
    ["{method}", "{route}"],
    {
        "method": "method",
        "route": "route",
        "status": "status",
        "group": "group",
    },
    [metrics.InspectType.TIMER, metrics.InspectType.COUNTER],
)

_COUNTER_RENDER = _metrics_stats.Counter(
    "render",
    "Pyramid render",
    ["render", "counter"],
    ["render", "timer"],
    ["{method}", "{route}"],
    {
        "method": "method",
        "route": "route",
        "status": "status",
        "group": "group",
    },
    [metrics.InspectType.TIMER, metrics.InspectType.COUNTER],
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
    kind: str, measure: _metrics_stats.Counter
) -> Callable[[pyramid.request.Request], None]:  # pragma: nocover
    inspect = measure.inspect()
    inspect.start()
    start = time.time()

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
        inspect.end(
            tags={
                "method": request.method,
                "route": name,
                "status": status,
                "group": str(status // 100),
            },
        )
        _add_server_metric(request, kind, duration=time.time() - start)

    return finished_cb


def _request_callback(event: pyramid.events.NewRequest) -> None:  # pragma: nocover
    """Finish the callback called when a new HTTP request is incoming."""
    event.request.add_finished_callback(_create_finished_cb("route", _COUNTER_ROUTES))


def _before_rendered_callback(event: pyramid.events.BeforeRender) -> None:  # pragma: nocover
    """Finish the callback called when the rendering is starting."""
    request = event.get("request", None)
    if request:
        request.add_finished_callback(_create_finished_cb("render", _COUNTER_RENDER))


def init(config: pyramid.config.Configurator) -> None:  # pragma: nocover
    """
    Subscribe to Pyramid events in order to get some stats on route time execution.

    Arguments:

        config: The Pyramid config
    """
    config.add_subscriber(_request_callback, pyramid.events.NewRequest)
    config.add_subscriber(_before_rendered_callback, pyramid.events.BeforeRender)
