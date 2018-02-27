"""
Generate statsd metrics.
"""

from abc import abstractmethod, ABCMeta
import contextlib
import logging
import pyramid.request
import re
import socket
import time
import threading
from typing import Mapping, Sequence, List, Generator, Any, Optional
from typing import MutableMapping, Tuple  # noqa  # pylint: disable=unused-import

from c2cwsgiutils import _utils

BACKENDS = {}  # type: MutableMapping[str, _BaseBackend]
LOG = logging.getLogger(__name__)


class Timer(object):
    """
    Allow to measure the duration of some activity
    """
    def __init__(self, key: Optional[Sequence[Any]]) -> None:
        self._key = key
        self._start = time.monotonic()

    def stop(self, key_final: Optional[Sequence[Any]]=None) -> float:
        duration = time.monotonic() - self._start
        if key_final is not None:
            self._key = key_final
        assert self._key is not None
        for backend in BACKENDS.values():
            backend.timer(self._key, duration)
        return duration


@contextlib.contextmanager
def timer_context(key: Sequence[Any]) -> Generator[None, None, None]:
    """
    Add a duration measurement to the stats using the duration the context took to run

    :param key: The path of the key, given as a list.
    """
    measure = timer(key)
    yield
    measure.stop()


@contextlib.contextmanager
def outcome_timer_context(key: List[Any]) -> Generator[None, None, None]:
    """
    Add a duration measurement to the stats using the duration the context took to run

    The given key is prepended with 'success' or 'failure' according to the context's outcome.

    :param key: The path of the key, given as a list.
    """
    measure = timer()
    try:
        yield
        measure.stop(key + ['success'])
    except Exception:
        measure.stop(key + ['failure'])
        raise


def timer(key: Optional[Sequence[Any]]=None) -> Timer:
    """
    Create a timer for the given key. The key can be omitted, but then need to be specified
    when stop is called.

    :param key: The path of the key, given as a list.
    :return: An instance of _Timer
    """
    assert key is None or isinstance(key, list)
    return Timer(key)


def set_gauge(key: Sequence[Any], value: float) -> None:
    """
    Set a gauge value

    :param key: The path of the key, given as a list.
    :param value: The new value of the gauge
    """
    for backend in BACKENDS.values():
        backend.gauge(key, value)


def increment_counter(key: Sequence[Any], increment: int=1) -> None:
    """
    Increment a counter value

    :param key: The path of the key, given as a list.
    :param increment: The increment
    """
    for backend in BACKENDS.values():
        backend.counter(key, increment)


class _BaseBackend(metaclass=ABCMeta):
    @abstractmethod
    def timer(self, key: Sequence[Any], duration: float) -> None:
        pass

    @abstractmethod
    def gauge(self, key: Sequence[Any], value: float) -> None:
        pass

    @abstractmethod
    def counter(self, key: Sequence[Any], increment: int) -> None:
        pass


class MemoryBackend(_BaseBackend):
    def __init__(self) -> None:
        self._timers = {}  # type: MutableMapping[str, Tuple[int, float, float, float]]
        self._gauges = {}  # type: MutableMapping[str, float]
        self._counters = {}  # type: MutableMapping[str, int]
        self._stats_lock = threading.Lock()
        LOG.info("Starting a MemoryBackend for stats")

    @staticmethod
    def _key(key: Sequence[Any]) -> str:
        return "/".join(str(v).replace('/', '_') for v in key)

    def timer(self, key: Sequence[Any], duration: float) -> None:
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

    def gauge(self, key: Sequence[Any], value: float) -> None:
        self._gauges[self._key(key)] = value

    def counter(self, key: Sequence[Any], increment: int) -> None:
        the_key = self._key(key)
        with self._stats_lock:
            self._counters[the_key] = self._counters.get(the_key, 0) + increment

    def get_stats(self, request: pyramid.request.Request) -> Mapping[str, Any]:
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


# https://github.com/prometheus/statsd_exporter/blob/master/mapper.go#L29
INVALID_KEY_CHARS = re.compile(r"[^a-zA-Z0-9_]")


class StatsDBackend(_BaseBackend):  # pragma: nocover
    def __init__(self, address: str, prefix: str) -> None:
        self._prefix = prefix
        if self._prefix != "" and not self._prefix.endswith("."):
            self._prefix += "."

        host, port = address.rsplit(":")
        host = host.strip("[]")
        addrinfo = socket.getaddrinfo(host, port, 0, 0, socket.IPPROTO_UDP)
        family, socktype, proto, _canonname, sockaddr = addrinfo[0]
        LOG.info("Starting a StatsDBackend for %s stats: %s -> %s", prefix, address, repr(sockaddr))

        self._socket = socket.socket(family, socktype, proto)
        self._socket.setblocking(False)
        self._socket.connect(sockaddr)

    @staticmethod
    def _key_entry(key_entry: Any) -> str:
        return INVALID_KEY_CHARS.sub("_", str(key_entry))

    def _key(self, key: Sequence[Any]) -> str:
        return (self._prefix + ".".join(map(StatsDBackend._key_entry, key)))[:450]

    def _send(self, message: str) -> None:
        # noinspection PyBroadException
        try:
            self._socket.send(message.encode('utf-8'))
        except Exception:
            pass  # Ignore errors (must survive if stats cannot be sent)

    def timer(self, key: Sequence[Any], duration: float) -> None:
        the_key = self._key(key)
        ms_duration = int(round(duration * 1000.0))
        ms_duration = max(ms_duration, 1)  # collectd would ignore events with zero durations
        message = "%s:%s|ms" % (the_key, ms_duration)
        self._send(message)

    def gauge(self, key: Sequence[Any], value: float) -> None:
        the_key = self._key(key)
        message = "%s:%s|g" % (the_key, value)
        self._send(message)

    def counter(self, key: Sequence[Any], increment: int) -> None:
        the_key = self._key(key)
        message = "%s:%s|c" % (the_key, increment)
        self._send(message)


def init_backends(settings: Mapping[str, str]) -> None:
    """
    Initialize the backends according to the configuration.

    :param settings: The Pyramid config
    """
    if _utils.env_or_settings(settings, "STATS_VIEW", "c2c.stats_view", False):  # pragma: nocover
        BACKENDS['memory'] = MemoryBackend()

    statsd_address = _utils.env_or_settings(settings, "STATSD_ADDRESS", "c2c.statsd_address", None)
    if statsd_address is not None:  # pragma: nocover
        statsd_prefix = _utils.env_or_settings(settings, "STATSD_PREFIX", "c2c.statsd_prefix", "")
        try:
            BACKENDS['statsd'] = StatsDBackend(statsd_address, statsd_prefix)
        except Exception:
            LOG.error("Failed configuring the statsd backend. Will continue without it.", exc_info=True)
