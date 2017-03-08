"""
Generate statsd metrics.
"""

import contextlib
import logging
import os
import re
import socket
import time
import threading

import pyramid.events
from pyramid.httpexceptions import HTTPException
import sqlalchemy.event

BACKENDS = []
LOG = logging.getLogger(__name__)


@contextlib.contextmanager
def timer_context(key):
    """
    Add a duration measurement to the stats using the duration the context took to run
    :param key: The path of the key, given as a list.
    """
    measure = timer(key)
    yield
    measure.stop()


def timer(key=None):
    """
    Create a timer for the given key. The key can be omitted, but then need to be specified
    when stop is called.
    :param key: The path of the key, given as a list.
    :return: An instance of _Timer
    """
    assert key is None or isinstance(key, list)
    return _Timer(key)


def set_gauge(key, value):
    """
    Set a gauge value
    :param key: The path of the key, given as a list.
    :param value: The new value of the gauge
    """
    for backend in BACKENDS:
        backend.gauge(key, value)


def increment_counter(key, increment=1):
    """
    Increment a counter value
    :param key: The path of the key, given as a list.
    :param increment: The increment
    """
    for backend in BACKENDS:
        backend.counter(key, increment)


class _Timer(object):
    """
    Allow to measure the duration of some activity
    """
    def __init__(self, key):
        self._key = key
        self._start = time.time()

    def stop(self, key_final=None):
        if key_final is not None:
            self._key = key_final
        for backend in BACKENDS:
            backend.timer(self._key, time.time() - self._start)


class _MemoryBackend(object):
    def __init__(self):
        self._timers = {}  # key => (nb, sum, min, max)
        self._gauges = {}  # key => value
        self._counters = {}  # key => value
        self._stats_lock = threading.Lock()
        LOG.info("Starting a MemoryBackend for stats")

    def _key(self, key):
        return "/".join(v.replace('/', '_') for v in key)

    def timer(self, key, duration):
        """
        Add a duration measurement to the stats.
        """
        the_key = self._key(key)
        with self._stats_lock:
            cur = self._timers.get(the_key, None)
            if cur is None:
                self._timers[the_key] = (1, duration, duration, duration)
            else:
                self._timers[the_key] = (cur[0] + 1, cur[1] + duration, min(cur[2], duration),
                                         max(cur[3], duration))

    def gauge(self, key, value):
        self._gauges[self._key(key)] = value

    def counter(self, key, increment):
        the_key = self._key(key)
        with self._stats_lock:
            self._counters[the_key] = self._counters.get(the_key, 0) + increment

    def get_stats(self, request):
        reset = request.params.get("reset", "0") == "1"
        with self._stats_lock:
            timers = {}
            for key, value in self._timers.items():
                timers[key] = {
                    "nb": value[0],
                    "avg_ms": int(round((value[1] / value[0]) * 1000.0)),
                    "min_ms": int(round(value[2] * 1000.0)),
                    "max_ms": int(round(value[3] * 1000.0)),
                }
            gauges = dict(self._gauges)
            counters = dict(self._counters)

            if reset:
                self._timers.clear()
                self._gauges.clear()
                self._counters.clear()
        return {"timers": timers, "gauges": gauges, "counters": counters}


INVALID_KEY_CHARS = re.compile(r"[:|\. ]")


class _StatsDBackend(object):  # pragma: nocover
    def __init__(self, address, prefix):
        self._prefix = prefix
        if self._prefix != "" and not self._prefix.endswith("."):
            self._prefix += "."

        host, port = address.rsplit(":")
        host = host.strip("[]")
        addrinfo = socket.getaddrinfo(host, port, 0, 0, socket.IPPROTO_UDP)
        family, socktype, proto, _canonname, sockaddr = addrinfo[0]
        LOG.info("Starting a StatsDBackend for %s stats: %s -> %s", prefix, address, repr(sockaddr))

        self._socket = socket.socket(family, socktype, proto)
        self._socket.setblocking(0)
        self._socket.connect(sockaddr)

    def _key(self, key):
        return (self._prefix + ".".join([INVALID_KEY_CHARS.sub("_", i) for i in key]))[:500]

    def _send(self, message):
        try:
            self._socket.send(message.encode('utf-8'))
        except:
            pass  # Ignore errors (must survive if stats cannot be sent)

    def timer(self, key, duration):
        the_key = self._key(key)
        message = "%s:%s|ms" % (the_key, int(round(duration * 1000.0)))
        self._send(message)

    def gauge(self, key, value):
        the_key = self._key(key)
        message = "%s:%s|g" % (the_key, value)
        self._send(message)

    def counter(self, key, increment):
        the_key = self._key(key)
        message = "%s:%s|c" % (the_key, increment)
        self._send(message)


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
    measure = timer()
    event.request.add_finished_callback(_create_finished_cb("route", measure))


def _before_rendered_callback(event):  # pragma: nocover
    """
    Callback called when the rendering is starting.
    """
    request = event.get("request", None)
    if request:
        measure = timer()
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
    measure = timer(["sql", _simplify_sql(statement)])

    def after(*_args, **_kwargs):
        measure.stop()

    sqlalchemy.event.listen(conn, "after_cursor_execute", after, once=True)


def _before_commit(session):  # pragma: nocover
    measure = timer(["sql", "commit"])

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


def _get_env_or_settings(config, what_env, what_vars, default):
    from_env = os.environ.get(what_env, None)
    if from_env is not None:  # pragma: nocover
        return from_env
    stats = config.get_settings().get("stats", {})
    return stats.get(what_vars, default)


def init_backends(config):
    """
    Initialize the backends according to the configuration.
    :param config: The Pyramid config
    """
    if _get_env_or_settings(config, "STATS_VIEW", "view", False):  # pragma: nocover
        memory_backend = _MemoryBackend()
        BACKENDS.append(memory_backend)

        config.add_route("read_stats_json", r"/stats.json", request_method="GET")
        config.add_view(memory_backend.get_stats, route_name="read_stats_json", renderer="json", http_cache=0)

    statsd_address = _get_env_or_settings(config, "STATSD_ADDRESS", "statsd_address", None)
    if statsd_address is not None:  # pragma: nocover
        statsd_prefix = _get_env_or_settings(config, "STATSD_PREFIX", "statsd_prefix", "")
        BACKENDS.append(_StatsDBackend(statsd_address, statsd_prefix))


def init(config):
    """
    Initialize the whole stats module.
    :param config: The Pyramid config
    """
    init_backends(config)
    if BACKENDS:  # pragma: nocover
        init_pyramid_spy(config)
        init_db_spy()
