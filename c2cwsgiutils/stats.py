"""
Generate statsd metrics.
"""

import contextlib
import logging
import re
import socket
import time
import threading

from c2cwsgiutils import _utils

BACKENDS = {}
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
    for backend in BACKENDS.values():
        backend.gauge(key, value)


def increment_counter(key, increment=1):
    """
    Increment a counter value

    :param key: The path of the key, given as a list.
    :param increment: The increment
    """
    for backend in BACKENDS.values():
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
        for backend in BACKENDS.values():
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


INVALID_KEY_CHARS = re.compile(r"[:|\.]")


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
        return (self._prefix + ".".join([INVALID_KEY_CHARS.sub("_", i) for i in key]))[:450]

    def _send(self, message):
        try:
            self._socket.send(message.encode('utf-8'))
        except:
            pass  # Ignore errors (must survive if stats cannot be sent)

    def timer(self, key, duration):
        the_key = self._key(key)
        ms_duration = int(round(duration * 1000.0))
        ms_duration = max(ms_duration, 1)  # collectd would ignore events with zero durations
        message = "%s:%s|ms" % (the_key, ms_duration)
        self._send(message)

    def gauge(self, key, value):
        the_key = self._key(key)
        message = "%s:%s|g" % (the_key, value)
        self._send(message)

    def counter(self, key, increment):
        the_key = self._key(key)
        message = "%s:%s|c" % (the_key, increment)
        self._send(message)


def init_backends(settings):
    """
    Initialize the backends according to the configuration.

    :param config: The Pyramid config
    """
    if _utils.env_or_settings(settings, "STATS_VIEW", "c2c.stats_view", False):  # pragma: nocover
        BACKENDS['memory'] = _MemoryBackend()

    statsd_address = _utils.env_or_settings(settings, "STATSD_ADDRESS", "c2c.statsd_address", None)
    if statsd_address is not None:  # pragma: nocover
        statsd_prefix = _utils.env_or_settings(settings, "STATSD_PREFIX", "c2c.statsd_prefix", "")
        BACKENDS['statsd'] = _StatsDBackend(statsd_address, statsd_prefix)
