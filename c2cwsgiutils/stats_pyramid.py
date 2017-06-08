"""
Generate statsd metrics for pyramid and SQLAlchemy events.
"""
import pyramid.events
from pyramid.httpexceptions import HTTPException
import re
import sqlalchemy.event

from c2cwsgiutils import stats, _utils


def _create_finished_cb(kind, measure):  # pragma: nocover
    def finished_cb(request):
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
        key = [kind, request.method, name, str(status)]
        measure.stop(key)
    return finished_cb


def _request_callback(event):  # pragma: nocover
    """
    Callback called when a new HTTP request is incoming.
    """
    measure = stats.timer()
    event.request.add_finished_callback(_create_finished_cb("route", measure))


def _before_rendered_callback(event):  # pragma: nocover
    """
    Callback called when the rendering is starting.
    """
    request = event.get("request", None)
    if request:
        measure = stats.timer()
        request.add_finished_callback(_create_finished_cb("render", measure))


def _simplify_sql(sql):
    """
    Simplify SQL statements to make them easier on the eye and shorter for the stats.
    """
    sql = " ".join(sql.split("\n"))
    sql = re.sub(r"  +", " ", sql)
    sql = re.sub(r"SELECT .*? FROM", "SELECT FROM", sql)
    sql = re.sub(r"INSERT INTO (.*?) \(.*", r"INSERT INTO \1", sql)
    sql = re.sub(r"SET .*? WHERE", "SET WHERE", sql)
    sql = re.sub(r"IN \((?:%\(\w+\)\w(?:, *)?)+\)", "IN (?)", sql)
    return re.sub(r"%\(\w+\)\w", "?", sql)


def _before_cursor_execute(conn, _cursor, statement,
                           _parameters, _context, _executemany):
    measure = stats.timer(["sql", _simplify_sql(statement)])

    def after(*_args, **_kwargs):
        measure.stop()

    sqlalchemy.event.listen(conn, "after_cursor_execute", after, once=True)


def _before_commit(session):  # pragma: nocover
    measure = stats.timer(["sql", "commit"])

    def after(*_args, **_kwargs):
        measure.stop()

    sqlalchemy.event.listen(session, "after_commit", after, once=True)


def init_db_spy():  # pragma: nocover
    """
    Subscribe to SQLAlchemy events in order to get some stats on DB interactions.
    """
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session
    sqlalchemy.event.listen(Engine, "before_cursor_execute", _before_cursor_execute)
    sqlalchemy.event.listen(Session, "before_commit", _before_commit)


def init_pyramid_spy(config):  # pragma: nocover
    """
    Subscribe to Pyramid events in order to get some stats on route time execution.

    :param config: The Pyramid config
    """
    config.add_subscriber(_request_callback, pyramid.events.NewRequest)
    config.add_subscriber(_before_rendered_callback, pyramid.events.BeforeRender)


def init(config):
    """
    Initialize the whole stats module.

    :param config: The Pyramid config
    """
    stats.init_backends(config.get_settings())
    if stats.BACKENDS:  # pragma: nocover
        if 'memory' in stats.BACKENDS:  # pragma: nocover
            config.add_route("c2c_read_stats_json", _utils.get_base_path(config) + r"/stats.json",
                             request_method="GET")
            config.add_view(stats.BACKENDS['memory'].get_stats, route_name="c2c_read_stats_json",
                            renderer="json", http_cache=0)
        init_pyramid_spy(config)
        init_db_spy()
