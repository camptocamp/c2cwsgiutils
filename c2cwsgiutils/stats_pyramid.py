"""
Generate statsd metrics for pyramid and SQLAlchemy events.
"""
import pyramid.config
import pyramid.events
import pyramid.request
from pyramid.httpexceptions import HTTPException
import re
import sqlalchemy.event
import sqlalchemy.orm
import sqlalchemy.engine
from typing import cast, Optional, Callable, Any

from c2cwsgiutils import stats, _utils


def _add_server_metric(request: pyramid.request.Request, name: str, duration: Optional[float]=None,
                       description: Optional[str]=None) -> None:
    # format: <name>;dur=<duration>;desc=<description>
    metric = name
    if duration is not None:
        metric += ';dur=' + str(round(duration * 1000))
    if description is not None:
        metric += ';desc=' + description

    if 'Server-Timing' not in request.response.headers:
        request.response.headers['Server-Timing'] = metric
    else:
        request.response.headers['Server-Timing'] += ', ' + metric


def _create_finished_cb(kind: str, measure: stats.Timer) -> Callable:  # pragma: nocover
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
            if kind == 'route':
                _add_server_metric(request, 'route', description=name)
        key = [kind, request.method, name, str(status)]
        duration = measure.stop(key)
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


def _jump_string(content: str, pos: int) -> int:
    quote_char = content[pos]
    pos += 1
    while pos < len(content):
        cur = content[pos]
        if cur == quote_char:
            if pos + 1 < len(content) and content[pos + 1] == quote_char:
                pos += 1
            else:
                return pos
        pos += 1
    return pos


def _eat_parenthesis(content: str) -> str:
    depth = 0
    pos = 0
    while pos < len(content):
        cur = content[pos]
        if cur == '(':
            depth += 1
        elif cur == ')':
            depth -= 1
            if depth == 0:
                pos += 1
                break
        elif cur in ('"', "'"):
            pos = _jump_string(content, pos)
        pos += 1
    return content[pos:]


def _simplify_sql(sql: str) -> str:
    """
    Simplify SQL statements to make them easier on the eye and shorter for the stats.
    """
    sql = " ".join(sql.split("\n"))
    sql = re.sub(r"  +", " ", sql)
    sql = re.sub(r"SELECT .*? FROM", "SELECT FROM", sql)
    sql = re.sub(r"INSERT INTO (.*?) \(.*", r"INSERT INTO \1", sql)
    sql = re.sub(r"SET .*? WHERE", "SET WHERE", sql)
    for in_ in reversed(list(re.compile(r" IN \(").finditer(sql))):
        before = sql[0:in_.start()]
        after = _eat_parenthesis(sql[in_.end() - 1:])
        sql = before + ' IN (?)' + after
    return re.sub(r"%\(\w+\)\w", "?", sql)


def _create_sqlalchemy_timer_cb(what: str) -> Callable:
    measure = stats.timer(["sql", what])

    def after(*_args: Any, **_kwargs: Any) -> None:
        measure.stop()
    return after


def _before_cursor_execute(conn: sqlalchemy.engine.Connection, _cursor: Any, statement: str,
                           _parameters: Any, _context: Any, _executemany: Any) -> None:
    sqlalchemy.event.listen(conn, "after_cursor_execute",
                            _create_sqlalchemy_timer_cb(_simplify_sql(statement)), once=True)


def _before_commit(session: sqlalchemy.orm.Session) -> None:  # pragma: nocover
    sqlalchemy.event.listen(session, "after_commit", _create_sqlalchemy_timer_cb("commit"), once=True)


def init_db_spy() -> None:  # pragma: nocover
    """
    Subscribe to SQLAlchemy events in order to get some stats on DB interactions.
    """
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session
    sqlalchemy.event.listen(Engine, "before_cursor_execute", _before_cursor_execute)
    sqlalchemy.event.listen(Session, "before_commit", _before_commit)


def init_pyramid_spy(config: pyramid.config.Configurator) -> None:  # pragma: nocover
    """
    Subscribe to Pyramid events in order to get some stats on route time execution.

    :param config: The Pyramid config
    """
    config.add_subscriber(_request_callback, pyramid.events.NewRequest)
    config.add_subscriber(_before_rendered_callback, pyramid.events.BeforeRender)


def init(config: pyramid.config.Configurator) -> None:
    """
    Initialize the whole stats module.

    :param config: The Pyramid config
    """
    stats.init_backends(config.get_settings())
    if stats.BACKENDS:  # pragma: nocover
        if 'memory' in stats.BACKENDS:  # pragma: nocover
            config.add_route("c2c_read_stats_json", _utils.get_base_path(config) + r"/stats.json",
                             request_method="GET")
            memory_backend = cast(stats.MemoryBackend, stats.BACKENDS['memory'])
            config.add_view(memory_backend.get_stats, route_name="c2c_read_stats_json",
                            renderer="fast_json", http_cache=0)
        init_pyramid_spy(config)
        init_db_spy()
