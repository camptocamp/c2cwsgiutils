"""
Generate statsd metrics.
"""

import contextlib
import logging
import os
import re
import socket
import threading
import time
from abc import ABCMeta, abstractmethod
from typing import (  # noqa  # pylint: disable=unused-import
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
)

import pyramid.request

from c2cwsgiutils import config_utils

LOG = logging.getLogger(__name__)
USE_TAGS_ENV = "STATSD_USE_TAGS"
TAG_PREFIX_ENV = "STATSD_TAG_"
USE_TAGS = config_utils.config_bool(os.environ.get(USE_TAGS_ENV, "0"))
TagType = Optional[Mapping[str, Any]]


class _BaseBackend(metaclass=ABCMeta):
    @abstractmethod
    def timer(self, key: Sequence[Any], duration: float, tags: TagType = None) -> None:
        pass

    @abstractmethod
    def gauge(self, key: Sequence[Any], value: float, tags: TagType = None) -> None:
        pass

    @abstractmethod
    def counter(self, key: Sequence[Any], increment: int, tags: TagType = None) -> None:
        pass


BACKENDS: MutableMapping[str, _BaseBackend] = {}


class Timer:
    """
    Allow to measure the duration of some activity
    """

    def __init__(self, key: Optional[Sequence[Any]], tags: TagType) -> None:
        self._key = key
        self._tags = tags
        self._start = time.monotonic()

    def stop(self, key_final: Optional[Sequence[Any]] = None, tags_final: TagType = None) -> float:
        duration = time.monotonic() - self._start
        if key_final is not None:
            self._key = key_final
        if tags_final is not None:
            self._tags = tags_final
        assert self._key is not None
        for backend in BACKENDS.values():
            backend.timer(self._key, duration, self._tags)
        return duration


@contextlib.contextmanager
def timer_context(key: Sequence[Any], tags: TagType = None) -> Generator[None, None, None]:
    """
    Add a duration measurement to the stats using the duration the context took to run

    :param key: The path of the key, given as a list.
    :param tags: Some tags to attach to the metric.
    """
    measure = timer(key, tags)
    yield
    measure.stop()


@contextlib.contextmanager
def outcome_timer_context(key: List[Any], tags: TagType = None) -> Generator[None, None, None]:
    """
    Add a duration measurement to the stats using the duration the context took to run

    The given key is prepended with 'success' or 'failure' according to the context's outcome.

    :param key: The path of the key, given as a list.
    :param tags: Some tags to attach to the metric.
    """
    measure = timer()
    try:
        yield
        if USE_TAGS:
            opt_tags = dict(tags) if tags is not None else {}
            opt_tags["success"] = 1
            measure.stop(key, opt_tags)
        else:
            measure.stop(key + ["success"], tags)
    except Exception:  # pylint: disable=broad-except
        if USE_TAGS:
            opt_tags = dict(tags) if tags is not None else {}
            opt_tags["success"] = 0
            measure.stop(key, opt_tags)
        else:
            measure.stop(key + ["failure"], tags)
        raise


def timer(key: Optional[Sequence[Any]] = None, tags: TagType = None) -> Timer:
    """
    Create a timer for the given key. The key can be omitted, but then need to be specified
    when stop is called.

    :param key: The path of the key, given as a list.
    :param tags: Some tags to attach to the metric.
    :return: An instance of _Timer
    """
    assert key is None or isinstance(key, list)
    return Timer(key, tags)


def set_gauge(key: Sequence[Any], value: float, tags: TagType = None) -> None:
    """
    Set a gauge value

    :param key: The path of the key, given as a list.
    :param value: The new value of the gauge
    :param tags: Some tags to attach to the metric.
    """
    for backend in BACKENDS.values():
        backend.gauge(key, value, tags)


def increment_counter(key: Sequence[Any], increment: int = 1, tags: TagType = None) -> None:
    """
    Increment a counter value

    :param key: The path of the key, given as a list.
    :param increment: The increment
    :param tags: Some tags to attach to the metric.
    """
    for backend in BACKENDS.values():
        backend.counter(key, increment, tags)


class MemoryBackend(_BaseBackend):
    def __init__(self) -> None:
        self._timers: MutableMapping[str, Tuple[int, float, float, float]] = {}
        self._gauges: MutableMapping[str, float] = {}
        self._counters: MutableMapping[str, int] = {}
        self._stats_lock = threading.Lock()
        LOG.info("Starting a MemoryBackend for stats")

    @staticmethod
    def _key_entry(key: str) -> str:
        return str(key).replace("/", "_")

    @staticmethod
    def _key(key: Sequence[Any], tags: TagType) -> str:
        result = "/".join(MemoryBackend._key_entry(v) for v in key)
        result += _format_tags(
            tags,
            prefix="/",
            tag_sep="/",
            kv_sep="=",
            key_formatter=MemoryBackend._key_entry,
            value_formatter=MemoryBackend._key_entry,
        )
        return result

    def timer(self, key: Sequence[Any], duration: float, tags: TagType = None) -> None:
        """
        Add a duration measurement to the stats.
        """
        the_key = self._key(key, tags)
        with self._stats_lock:
            cur = self._timers.get(the_key, None)
            if cur is None:
                self._timers[the_key] = (1, duration, duration, duration)
            else:
                self._timers[the_key] = (
                    cur[0] + 1,
                    cur[1] + duration,
                    min(cur[2], duration),
                    max(cur[3], duration),
                )

    def gauge(self, key: Sequence[Any], value: float, tags: TagType = None) -> None:
        self._gauges[self._key(key, tags)] = value

    def counter(self, key: Sequence[Any], increment: int, tags: TagType = None) -> None:
        the_key = self._key(key, tags)
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
INVALID_TAG_VALUE_CHARS = re.compile(r"[,#|]")


class StatsDBackend(_BaseBackend):  # pragma: nocover
    def __init__(self, address: str, prefix: str, tags: Optional[Dict[str, str]] = None) -> None:
        self._prefix = prefix
        self._tags = tags
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

    @staticmethod
    def _tag_value(tag_value: Any) -> str:
        return INVALID_TAG_VALUE_CHARS.sub("_", str(tag_value))

    def _key(self, key: Sequence[Any]) -> str:
        return (self._prefix + ".".join(map(StatsDBackend._key_entry, key)))[:450]

    def _merge_tags(self, tags: TagType) -> TagType:
        if tags is None:
            return self._tags
        elif self._tags is None:
            return tags
        else:
            tmp = dict(self._tags)
            tmp.update(tags)
            return tmp

    def _send(self, message: str, tags: TagType) -> None:
        tags = self._merge_tags(tags)
        message += _format_tags(
            tags,
            prefix="|#",
            tag_sep=",",
            kv_sep=":",
            key_formatter=StatsDBackend._key_entry,
            value_formatter=StatsDBackend._tag_value,
        )
        try:
            self._socket.send(message.encode("utf-8"))
        except Exception:  # nosec  # pylint: disable=broad-except
            pass  # Ignore errors (must survive if stats cannot be sent)

    def timer(self, key: Sequence[Any], duration: float, tags: TagType = None) -> None:
        the_key = self._key(key)
        ms_duration = int(round(duration * 1000.0))
        ms_duration = max(ms_duration, 1)  # collectd would ignore events with zero durations
        message = "%s:%s|ms" % (the_key, ms_duration)
        self._send(message, tags)

    def gauge(self, key: Sequence[Any], value: float, tags: TagType = None) -> None:
        the_key = self._key(key)
        message = "%s:%s|g" % (the_key, value)
        self._send(message, tags)

    def counter(self, key: Sequence[Any], increment: int, tags: TagType = None) -> None:
        the_key = self._key(key)
        message = "%s:%s|c" % (the_key, increment)
        self._send(message, tags)


def init_backends(settings: Optional[Mapping[str, str]] = None) -> None:
    """
    Initialize the backends according to the configuration.

    :param settings: The Pyramid config
    """
    if config_utils.env_or_settings(settings, "STATS_VIEW", "c2c.stats_view", False):  # pragma: nocover
        BACKENDS["memory"] = MemoryBackend()

    statsd_address = config_utils.env_or_settings(settings, "STATSD_ADDRESS", "c2c.statsd_address", None)
    if statsd_address is not None:  # pragma: nocover
        statsd_prefix = config_utils.env_or_settings(settings, "STATSD_PREFIX", "c2c.statsd_prefix", "")
        statsd_tags = get_env_tags()
        try:
            BACKENDS["statsd"] = StatsDBackend(statsd_address, statsd_prefix, statsd_tags)
        except Exception:  # pylint: disable=broad-except
            LOG.error("Failed configuring the statsd backend. Will continue without it.", exc_info=True)


def _format_tags(
    tags: Optional[Mapping[str, Any]],
    prefix: str,
    tag_sep: str,
    kv_sep: str,
    key_formatter: Callable[[str], str],
    value_formatter: Callable[[str], str],
) -> str:
    if tags:
        return prefix + tag_sep.join(
            key_formatter(k) + kv_sep + value_formatter(v) for k, v in sorted(tags.items())
        )
    else:
        return ""


def get_env_tags() -> Dict[str, str]:
    tags = {}
    for name, value in os.environ.items():
        if name.startswith(TAG_PREFIX_ENV):
            tags[name[len(TAG_PREFIX_ENV) :].lower()] = value
    return tags
