"""Used to publish metrics to Prometheus."""

import re
import socket
import time
import warnings
from enum import Enum
from os import listdir
from typing import Any, Callable, Dict, Generic, List, Mapping, Optional, Tuple, TypedDict, TypeVar, Union

import pyramid.request
import pyramid.response

from c2cwsgiutils.debug.utils import dump_memory_maps


class ProviderData(TypedDict):
    """The provider data."""

    name: str
    help: str
    type: str
    extend: bool
    data: List[Tuple[Dict[str, str], Union[int, float]]]


class BaseProvider:
    """Provide set of Prometheus values."""

    def get_full_data(self) -> List[ProviderData]:
        """Get all the provided data."""
        return []


class Provider(BaseProvider):
    """The provider interface."""

    def __init__(self, name: str, help_: str, type_: str = "gauge", extend: bool = True):
        self.name = name
        self.help = help_
        self.type = type_
        self.extend = extend

    def get_data(self) -> List[Tuple[Dict[str, str], Union[int, float]]]:
        """Get all the provided data."""

        raise NotImplementedError()

    def get_full_data(self) -> List[ProviderData]:
        """Get all the provided data."""

        return [
            {
                "name": self.name,
                "help": self.help,
                "type": self.type,
                "extend": self.extend,
                "data": self.get_data(),
            }
        ]


_PROVIDERS: List[BaseProvider] = []


POD_NAME = socket.gethostname()
SERVICE_NAME = re.match("^(.+)-[0-9a-f]+-[0-9a-z]+$", POD_NAME)


def add_provider(provider: BaseProvider) -> None:
    """Add the provider."""
    _PROVIDERS.append(provider)


def _metrics() -> str:
    result: List[str] = []

    for provider in _PROVIDERS:
        for data in provider.get_full_data():
            result += [
                f"# HELP {data['name']} {data['help']}",
                f"# TYPE {data['name']} {data['type']}",
            ]
            for attributes, value in data["data"]:
                attrib = {}
                if data["extend"]:
                    attrib["pod_name"] = POD_NAME
                    if SERVICE_NAME is not None:
                        attrib["service_name"] = SERVICE_NAME.group(1)
                attrib.update(attributes)
                dbl_quote = '"'
                printable_attributes = ",".join(
                    [f'{k}="{v.replace(dbl_quote, "_")}"' for k, v in attrib.items()]
                )
                result.append(f"{data['name']}{{{printable_attributes}}} {value}")

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


class Value:
    """The value store for a Prometheus gauge."""

    def get_value(self) -> Union[int, float]:
        raise NotImplementedError()


_Value = TypeVar("_Value", bound=Value)


class _Data(BaseProvider, Generic[_Value]):
    def __init__(self) -> None:
        self.data: List[Tuple[Dict[str, str], _Value]] = []

    def get_value(self, key: Optional[Mapping[str, Optional[str]]]) -> _Value:
        key = key or {}
        for attributes, value in self.data:
            if len(attributes) != len(key):
                continue
            for k, v in key.items():
                if attributes.get(k) != v:
                    break
            return value
        return self.new_value()

    def get_data(self) -> List[Tuple[Dict[str, str], Union[int, float]]]:
        """Get the values."""
        return [(k, v.get_value()) for k, v in self.data]

    def new_value(self) -> _Value:
        raise NotImplementedError()


class InspectType(Enum):
    """The type of inspection."""

    COUNTER = "counter"
    TIMER = "timer"


class Inspect:
    """A class used to inspect a part ov code."""

    _start: float = 0

    def __init__(
        self, gauge: "AutoCounter", tags: Optional[Mapping[str, Optional[str]]], add_status: bool = False
    ):
        self.gauge = gauge
        self.tags = tags
        self.add_status = add_status

    def __enter__(self) -> "Inspect":
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
        self.gauge.increment(
            time.monotonic() - self._start,
            {
                **({"status": "success" if success else "failure"} if self.add_status else {}),
                **(self.tags or {}),
                **(tags or {}),
            },
        )


class GaugeValue(Value):
    """The value store for a Prometheus gauge."""

    value: Union[int, float] = 0

    def get_value(self) -> Union[int, float]:
        return self.value

    def set_value(self, value: Union[int, float]) -> None:
        self.value = value


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


class CounterValue(Value):
    """The value store for a Prometheus gauge."""

    value: Union[int, float] = 0

    def get_value(self) -> Union[int, float]:
        return self.value

    def inc(self, value: Union[int, float] = 1) -> None:
        self.value += value


class SimpleCounter(_Data[CounterValue]):
    """Provide a counter that should be manually increase."""

    def __init__(self, name: str, help_: str, extend: bool = True):
        self.name = name
        self.help = help_
        self.type = "gauge"
        self.extend = extend
        super().__init__()

    def new_value(self) -> CounterValue:
        return CounterValue()


class AutoCounter(_Data[CounterValue]):
    """The provider interface."""

    def __init__(
        self,
        name: str,
        help_: str,
        extend: bool = True,
        inspect_type: Optional[List[InspectType]] = None,
        add_success: bool = False,
    ):
        self.name = name
        self.help = help_
        self.extend = extend
        self.add_success = add_success
        self.sub_counters: Dict[InspectType, SimpleCounter] = {}
        inspect_type = inspect_type or []
        for type_ in inspect_type:
            sub_name = name
            sub_help = help_
            if len(inspect_type) > 1:
                if type_ == InspectType.TIMER:
                    sub_name += "_timer"
                    sub_help += " [seconds]"
                elif type_ == InspectType.COUNTER:
                    sub_name += "_count"
                    sub_help += " [nb]"

            self.sub_counters[type_] = SimpleCounter(sub_name, sub_help, extend)
        super().__init__()

    def new_value(self) -> CounterValue:
        # Raise exception because this function should never be called
        raise NotImplementedError()

    def get_full_data(self) -> List[ProviderData]:
        results: List[ProviderData] = []
        for counter in self.sub_counters.values():
            results += counter.get_full_data()
        return results

    def increment(self, time_: float, tags: Optional[Mapping[str, Optional[str]]] = None) -> None:
        tags = tags or {}
        for inspect_type, counter in self.sub_counters.items():
            if inspect_type == InspectType.TIMER:
                counter.get_value(tags).inc(time_)
            elif inspect_type == InspectType.COUNTER:
                counter.get_value(tags).inc()

    def inspect(self, tags: Optional[Mapping[str, Optional[str]]] = None) -> Inspect:
        return Inspect(self, tags)
