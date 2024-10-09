"""Every thing we needs to have the metrics in Prometheus."""

import os
import re
from collections.abc import Generator, Iterable
from typing import Any, Optional, TypedDict, cast

import prometheus_client
import prometheus_client.core
import prometheus_client.metrics_core
import prometheus_client.multiprocess
import prometheus_client.registry
import pyramid.config

from c2cwsgiutils import broadcast, redis_utils
from c2cwsgiutils.debug.utils import dump_memory_maps

_NUMBER_RE = re.compile(r"^[0-9]+$")
MULTI_PROCESS_COLLECTOR_BROADCAST_CHANNELS = [
    "c2cwsgiutils_prometheus_collector_gc",
    "c2cwsgiutils_prometheus_collector_process",
]


def start(registry: Optional[prometheus_client.CollectorRegistry] = None) -> None:
    """Start separate HTTP server to provide the Prometheus metrics."""
    if os.environ.get("C2C_PROMETHEUS_PORT") is not None:
        broadcast.includeme()

        registry = prometheus_client.CollectorRegistry() if registry is None else registry
        registry.register(MemoryMapCollector())
        registry.register(prometheus_client.PLATFORM_COLLECTOR)
        registry.register(MultiProcessCustomCollector())
        prometheus_client.multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
        prometheus_client.start_http_server(int(os.environ["C2C_PROMETHEUS_PORT"]), registry=registry)


def includeme(config: pyramid.config.Configurator) -> None:
    """Initialize prometheus_client in pyramid context."""
    del config  # unused
    broadcast.subscribe("c2cwsgiutils_prometheus_collector_gc", _broadcast_collector_gc)
    broadcast.subscribe("c2cwsgiutils_prometheus_collector_process", _broadcast_collector_process)


def build_metric_name(postfix: str) -> str:
    """Build the metric name with the prefix from the environment variable."""
    return os.environ.get("C2C_PROMETHEUS_PREFIX", "c2cwsgiutils_") + postfix


def cleanup() -> None:
    """Cleanup the prometheus_client registry."""
    redis_utils.cleanup()
    broadcast.cleanup()


class SerializedSample(TypedDict):
    """Represent the serialized sample."""

    name: str
    labels: dict[str, str]
    value: float


class SerializedMetric(TypedDict):
    """Represent the serialized gauge."""

    type: str
    args: dict[str, Any]
    samples: list[SerializedSample]


def _broadcast_collector_gc() -> list[SerializedMetric]:
    """Get the collected GC gauges."""
    return serialize_collected_data(prometheus_client.GC_COLLECTOR)


def _broadcast_collector_process() -> list[SerializedMetric]:
    """Get the collected process gauges."""
    return serialize_collected_data(prometheus_client.PROCESS_COLLECTOR)


def serialize_collected_data(collector: prometheus_client.registry.Collector) -> list[SerializedMetric]:
    """Serialize the data from the custom collector."""
    gauges: list[SerializedMetric] = []
    for process_gauge in collector.collect():
        gauge: SerializedMetric = {
            "type": "<to be defined>",
            "args": {
                "name": process_gauge.name,
                "documentation": process_gauge.documentation,
                "unit": process_gauge.unit,
            },
            "samples": [],
        }

        if isinstance(process_gauge, prometheus_client.core.GaugeMetricFamily):
            gauge["type"] = "gauge"
        elif isinstance(process_gauge, prometheus_client.core.CounterMetricFamily):
            gauge["type"] = "counter"
        else:
            raise NotImplementedError()
        for sample in process_gauge.samples:
            gauge["samples"].append(
                {
                    "name": sample.name,
                    "labels": {"pid": str(os.getpid()), **sample.labels},
                    "value": sample.value,
                },
            )
        gauges.append(gauge)
    return gauges


class MultiProcessCustomCollector(prometheus_client.registry.Collector):
    """Get the metrics from the custom collectors."""

    def collect(self) -> Generator[prometheus_client.core.Metric, None, None]:
        results: list[list[SerializedMetric]] = []
        for channel in MULTI_PROCESS_COLLECTOR_BROADCAST_CHANNELS:
            result = broadcast.broadcast(channel, expect_answers=True)
            if result is not None:
                results.extend(cast(Iterable[list[SerializedMetric]], result))
        return _deserialize_collected_data(results)


def _deserialize_collected_data(
    results: list[list[SerializedMetric]],
) -> Generator[prometheus_client.core.Metric, None, None]:
    for serialized_collection in results:
        if serialized_collection is None:
            continue

        for serialized_metric in serialized_collection:
            if serialized_metric is None:
                continue

            if serialized_metric["type"] == "gauge":
                metric: prometheus_client.core.Metric = prometheus_client.core.GaugeMetricFamily(
                    **serialized_metric["args"]
                )
            elif serialized_metric["type"] == "counter":
                metric = prometheus_client.core.CounterMetricFamily(**serialized_metric["args"])
            else:
                raise NotImplementedError()
            for sample in serialized_metric["samples"]:
                metric.samples.append(
                    prometheus_client.metrics_core.Sample(**sample),  # type: ignore[attr-defined]
                )
            yield metric


class MemoryMapCollector(prometheus_client.registry.Collector):
    """The Linux memory map provider."""

    def __init__(self, memory_type: str = "pss", pids: Optional[list[str]] = None):
        """
        Initialize.

        Arguments:
            memory_type: can be rss, pss or size
            pids: the list of pids or none
        """
        super().__init__()
        self.memory_type = memory_type
        self.pids = pids

    def collect(self) -> Generator[prometheus_client.core.GaugeMetricFamily, None, None]:
        """Get the gauge from smap file."""
        gauge = prometheus_client.core.GaugeMetricFamily(
            build_metric_name(f"process_smap_{self.memory_type}"),
            f"Container smap used {self.memory_type.capitalize()}",
            labels=["pid", "name"],
            unit="bytes",
        )

        for pid in (
            [p for p in os.listdir("/proc/") if _NUMBER_RE.match(p)] if self.pids is None else self.pids
        ):
            for e in dump_memory_maps(pid):
                gauge.add_metric([pid, e["name"]], e[self.memory_type + "_kb"] * 1024)
        yield gauge
