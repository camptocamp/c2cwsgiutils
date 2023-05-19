"""Used to publish metrics to Prometheus."""

import re
import socket
import warnings
from os import listdir
from typing import Any, Dict, Generic, List, Optional, Tuple, Union

import pyramid.request
import pyramid.response

from c2cwsgiutils.debug.utils import dump_memory_maps


class Provider:
    """The provider interface."""

    def __init__(self, name: str, help_: str, type_: str = "gauge", extend: bool = True):
        self.name = name
        self.help = help_
        self.type = type_
        self.extend = extend

    def get_data(self) -> List[Tuple[Dict[str, str], Union[int, float]]]:
        """Get empty response, should be defined in the specific provider."""
        return []


_PROVIDERS = []


POD_NAME = socket.gethostname()
SERVICE_NAME = re.match("^(.+)-[0-9a-f]+-[0-9a-z]+$", POD_NAME)


def add_provider(provider: Provider) -> None:
    """Add the provider."""
    _PROVIDERS.append(provider)


def _metrics() -> str:
    result: List[str] = []

    for provider in _PROVIDERS:
        result += [
            f"# HELP {provider.name} {provider.help}",
            f"# TYPE {provider.name} {provider.type}",
        ]
        for attributes, value in provider.get_data():
            attrib = {}
            if provider.extend:
                attrib["pod_name"] = POD_NAME
                if SERVICE_NAME is not None:
                    attrib["service_name"] = SERVICE_NAME.group(1)
            attrib.update(attributes)
            dbl_quote = '"'
            printable_attribs = ",".join([f'{k}="{v.replace(dbl_quote, "_")}"' for k, v in attrib.items()])
            result.append(f"{provider.name}{{{printable_attribs}}} {value}")

    return "\n".join(result)


def _view(request: pyramid.request.Request) -> pyramid.response.Response:
    request.response.text = _metrics()
    return request.response


NUMBER_RE = re.compile(r"^[0-9]+$")


class MemoryMapProvider(Provider):
    """The Linux memory map provider."""

    def __init__(self, memory_type: str = "pss", pids: Optional[List[str]] = None):
        """
        Initialize.

        Arguments:

            memory_type: can be rss, pss or size
            pids: the list of pids or none
        """
        super().__init__(
            f"pod_process_smap_{memory_type}_kb",
            f"Container smap used {memory_type.capitalize()}",
        )
        self.memory_type = memory_type
        self.pids = pids

    def get_data(self) -> List[Tuple[Dict[str, Any], Union[int, float]]]:
        """Get empty response, should be defined in the specific provider."""
        results: List[Tuple[Dict[str, Any], Union[int, float]]] = []
        for pid in [p for p in listdir("/proc/") if NUMBER_RE.match(p)] if self.pids is None else self.pids:
            results += [
                ({"pid": pid, "name": e["name"]}, e[self.memory_type + "_kb"]) for e in dump_memory_maps(pid)
            ]
        return results


def init(config: pyramid.config.Configurator) -> None:
    """Initialize the metrics view, , for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """Initialize the metrics view."""
    config.add_route("c2c_metrics", r"/metrics", request_method="GET")
    config.add_view(_view, route_name="c2c_metrics", http_cache=0)
    add_provider(MemoryMapProvider())


class _Value:
    def get_value(self) -> Union[int, float]:
        raise NotImplementedError()


Value = TypeVar("Value", bound=_Value)


class _Data(Provider, Generic[Value]):
    def __init__(self):
        self.data: List[Tuple[Dict[str, str], Value]] = []

    def get_value(self, key: Dict[str, str]) -> Value:
        for attributes, value in self.data:
            if len(attributes) != len(key):
                continue
            for k, v in key.items():
                if attributes.get(k) != v:
                    break
            return value
        return None

    def get_data(self) -> List[Tuple[Dict[str, str], Union[int, float]]]:
        """Get the values."""
        return [(k, v.get_value()) for k, v in self.data]

    def new_value(self) -> Value:
        raise NotImplementedError()


class Gauge(_Data[GaugeValue]):
    """The provider interface."""

    def __init__(self, name: str, help_: str, extend: bool = True):
        self.name = name
        self.help = help_
        self.type = "gauge"
        self.extend = extend
        super().__init__()

    def new_value(self) -> GaugeValue:
        return GaugeValue()


class TimerGauge:
    """An interface to use a Prometheus gauge to get elapsed time with a decorator or a `with` statement."""

    _start: float = 0

    def __init__(self, gauge: "CounterValue", add_status: bool = False):
        self.gauge = gauge
        self.add_status = add_status

    def __enter__(self) -> "TimerGauge":
        self._start = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.gauge.inc(time.time() - self._start, {"status": "success" if exc_val is None else "failure"})

    def __call__(self, function: Function) -> Function:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return function(*args, **kwargs)

        return wrapper


class StatusGauge(_Data[StatusGaugeValue]):
    """The provider interface."""

    def __init__(self, name: str, help_: str, extend: bool = True):
        self.name = name
        self.help = help_
        self.type = "gauge"
        self.extend = extend
        super().__init__()

    def new_value(self) -> StatusGaugeValue:
        return StatusGaugeValue()


class CounterGauge:
    """An interface to use a Prometheus gauge to count with a decorator or a `with` statement."""

    def __init__(self, gauge: "CounterValue"):
        self.gauge = gauge

    def __enter__(self) -> "CounterGauge":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.gauge.inc()

    def __call__(self, function: Function) -> Function:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return function(*args, **kwargs)

        return wrapper


class CounterValue(_Value):
    """The value store for a Prometheus gauge."""

    value: Union[int, float] = 0

    def get_value(self) -> Union[int, float]:
        return value

    def inc(self, increment: Union[int, float] = 1) -> None:
        self.value += value

    def timer(self) -> TimerGauge:
        return TimerGauge(self)

    def count(self) -> CounterGauge:
        return CounterGauge(self)


class Counter(_Data[CounterValue]):
    """The provider interface."""

    def __init__(self, name: str, help_: str, extend: bool = True):
        self.name = name
        self.help = help_
        self.type = "gauge"
        self.extend = extend
        super().__init__()

    def new_value(self) -> CounterValue:
        return CounterValue()


class CounterStatusTimer:
    """An interface to use a Prometheus gauge to get elapsed time with a decorator or a `with` statement."""

    _start: float = 0

    def __init__(self, gauge: "CounterStatusValue"):
        self.gauge = gauge

    def __enter__(self) -> "CounterStatusTimer":
        self._start = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_val is None:
            gauge.inc_success(time.time() - self._start)
        else:
            gauge.inc_failure(time.time() - self._start)

    def __call__(self, function: Function) -> Function:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return function(*args, **kwargs)

        return wrapper


class CounterStatusGauge:
    """An interface to use a Prometheus gauge to count with a decorator or a `with` statement."""

    def __init__(self, gauge: "CounterStatusValue"):
        self.gauge = gauge

    def __enter__(self) -> "CounterStatusGauge":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_val is None:
            self.gauge.inc_success()
        else:
            self.gauge.inc_failure()

    def __call__(self, function: Function) -> Function:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return function(*args, **kwargs)

        return wrapper


class CounterStatusValue(_Value):
    """The value store for a Prometheus gauge."""

    success: int = 0
    failure: int = 0

    def get_success(self) -> int:
        return success

    def get_failure(self) -> int:
        return failure

    def inc_success(self, increment: Union[int, float] = 1) -> None:
        self.success += value

    def inc_failure(self, increment: Union[int, float] = 1) -> None:
        self.failure += value

    def timer(self) -> CounterStatusTimer:
        return CounterStatusTimer(self)

    def count(self) -> CounterStatusGauge:
        return CounterStatusGauge(self)


class CounterStatus(_Data[CounterStatusValue]):
    """The provider interface."""

    def __init__(self, name: str, help_: str, extend: bool = True):
        self.name = name
        self.help = help_
        self.type = "gauge"
        self.extend = extend
        super().__init__()

    def new_value(self) -> CounterStatusValue:
        return CounterStatusValue()

    def get_data(self) -> List[Tuple[Dict[str, str], Union[int, float]]]:
        """Get the values."""
        return [
            *[({"status": "success", **k}, v.get_success()) for k, v in self.data],
            *[({"status": "failure", **k}, v.get_failure()) for k, v in self.data],
        ]
