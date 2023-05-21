"""Module used to add metrics that work with prometheus and statsd."""


import os
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Union

from c2cwsgiutils import metrics, stats


class Gauge:
    """Provide a simple Prometheus gauge."""

    def __init__(
        self,
        prometheus_name: str,
        description: str,
        statsd_pattern: List[str],
        statsd_pattern_no_tags: List[str],
        statsd_tags_mapping: Dict[str, str],
    ):
        self.prometheus = os.environ.get("PROMETHEUS_PREFIX") is not None
        if self.prometheus:
            self.prometheus_gauge = metrics.Gauge(
                os.environ.get("PROMETHEUS_PREFIX", "") + prometheus_name,
                description,
            )
            metrics.add_provider(self.prometheus_gauge)
        self.statsd_pattern = statsd_pattern
        self.statsd_pattern_no_tags = statsd_pattern_no_tags
        self.statsd_tags_mapping = statsd_tags_mapping

    def set(self, value: float, tags: Optional[Mapping[str, Optional[str]]] = None) -> None:
        if self.prometheus:
            self.prometheus_gauge.get_value(tags).set_value(value)
        else:
            tags = tags or {}
            if stats.USE_TAGS:
                statsd_tags = {
                    self.statsd_tags_mapping[k]: v
                    for k, v in tags.items()
                    if k in self.statsd_tags_mapping.keys()
                }
                stats.set_gauge([e.format(**tags) for e in self.statsd_pattern], value, statsd_tags)
            else:
                stats.set_gauge(
                    [
                        *[e.format(**tags) for e in self.statsd_pattern],
                        *[e.format(**tags) for e in self.statsd_pattern_no_tags],
                    ],
                    value,
                )


class _Inspect:
    """A class used to inspect a part ov code."""

    _start: float = 0

    def __init__(self, gauge: "Counter", tags: Optional[Mapping[str, Optional[str]]]):
        self.gauge = gauge
        self.tags = tags or {}

    def __enter__(self) -> "_Inspect":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.end(exc_val is None)

    def __call__(self, function: Callable) -> Callable:  # type: ignore[type-arg]
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return function(*args, **kwargs)

        return wrapper

    def start(self) -> None:
        self._start = time.monotonic()

    def end(self, success: bool = True, tags: Optional[Dict[str, str]] = None) -> None:
        assert self._start > 0
        self.gauge.increment_counter({**self.tags, **(tags or {})}, time.monotonic() - self._start, success)


class Counter:
    """Provide a counter for Prometheus or StatsD."""

    def __init__(
        self,
        prometheus_name: str,
        description: str,
        statsd_pattern_counter: List[str],
        statsd_pattern_timer: List[str],
        statsd_pattern_no_tags: List[str],
        statsd_tags_mapping: Dict[str, str],
        inspect_type: Optional[List[metrics.InspectType]] = None,
        add_success: bool = False,
    ):
        self.prometheus = os.environ.get("PROMETHEUS_PREFIX") is not None
        if self.prometheus:
            if inspect_type is None:
                self.prometheus_gauge: Union[metrics.Counter, metrics.CounterInspector] = metrics.Counter(
                    os.environ.get("PROMETHEUS_PREFIX", "") + prometheus_name, description
                )
            else:
                self.prometheus_gauge = metrics.CounterInspector(
                    os.environ.get("PROMETHEUS_PREFIX", "") + prometheus_name,
                    description,
                    inspect_type=inspect_type,
                    add_success=add_success,
                )
            metrics.add_provider(self.prometheus_gauge)
        self.statsd_pattern_counter = statsd_pattern_counter
        self.statsd_pattern_timer = statsd_pattern_timer
        self.statsd_pattern_no_tags = statsd_pattern_no_tags
        self.statsd_tags_mapping = statsd_tags_mapping
        self.inspect_type = inspect_type
        self.add_success = add_success

    def inspect(self, tags: Optional[Mapping[str, Optional[str]]] = None) -> Union[metrics.Inspect, _Inspect]:
        if self.prometheus:
            assert isinstance(self.prometheus_gauge, metrics.CounterInspector)
            return self.prometheus_gauge.inspect(tags)
        else:
            return _Inspect(self, tags)

    def increment_counter(
        self,
        tags: Optional[Mapping[str, Optional[str]]],
        value: Union[int, float] = 0.0,
        success: bool = True,
    ) -> None:
        tags = tags or {}
        if self.inspect_type is None:
            assert isinstance(value, int)
            statsd_pattern = self.statsd_pattern_counter
            if stats.USE_TAGS:
                statsd_tags = {
                    self.statsd_tags_mapping[k]: v
                    for k, v in tags.items()
                    if k in self.statsd_tags_mapping.keys()
                }
                stats.increment_counter([e.format(**tags) for e in statsd_pattern], value, statsd_tags)
            else:
                stats.increment_counter(
                    [
                        *[e.format(**tags) for e in statsd_pattern],
                        *[e.format(**tags) for e in self.statsd_pattern_no_tags],
                    ],
                    value,
                )
        else:
            for inspect_type in self.inspect_type:
                if inspect_type == metrics.InspectType.TIMER:
                    statsd_pattern = self.statsd_pattern_timer
                elif inspect_type == metrics.InspectType.COUNTER:
                    statsd_pattern = self.statsd_pattern_counter
                if self.add_success:
                    statsd_pattern.append("success" if success else "failure")
                if stats.USE_TAGS:
                    statsd_tags = {
                        self.statsd_tags_mapping[k]: v
                        for k, v in tags.items()
                        if k in self.statsd_tags_mapping.keys()
                    }
                    if inspect_type == metrics.InspectType.TIMER:
                        stats.increment_timer([e.format(**tags) for e in statsd_pattern], value, statsd_tags)
                    elif inspect_type == metrics.InspectType.COUNTER:
                        stats.increment_counter([e.format(**tags) for e in statsd_pattern], 1, statsd_tags)
                else:
                    if inspect_type == metrics.InspectType.TIMER:
                        stats.increment_timer(
                            [
                                *[e.format(**tags) for e in statsd_pattern],
                                *[e.format(**tags) for e in self.statsd_pattern_no_tags],
                            ],
                            value,
                        )
                    elif inspect_type == metrics.InspectType.COUNTER:
                        stats.increment_counter(
                            [
                                *[e.format(**tags) for e in statsd_pattern],
                                *[e.format(**tags) for e in self.statsd_pattern_no_tags],
                            ],
                            1,
                        )
