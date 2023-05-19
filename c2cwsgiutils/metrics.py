"""Used to publish metrics to Prometheus."""

import re
import socket
import warnings
from os import listdir
from typing import Any, Dict, Generic, List, Optional, Tuple, TypedDict, Union

import pyramid.request
import pyramid.response

from c2cwsgiutils.debug.utils import dump_memory_maps


class ProviderData(TypedDict):
    """The provider data."""

    name: str
    help_: str
    type_: str
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
        return []

    def get_full_data(self) -> List[ProviderData]:
        """Get all the provided data."""
        return [
            {name: self.name, help_: self.help, type_: self.type, extend: self.extend, data: self.get_data()}
        ]


_PROVIDERS = []


POD_NAME = socket.gethostname()
SERVICE_NAME = re.match("^(.+)-[0-9a-f]+-[0-9a-z]+$", POD_NAME)


def add_provider(provider: Provider) -> None:
    """Add the provider."""
    _PROVIDERS.append(provider)


def _metrics() -> str:
    result: List[str] = []

    for provider in _PROVIDERS:
        for data in provider.get_full_data():
            result += [
                f"# HELP {data.name} {data.help}",
                f"# TYPE {data.name} {data.type}",
            ]
            for attributes, value in data.data:
                attrib = {}
                if data.extend:
                    attrib["pod_name"] = POD_NAME
                    if SERVICE_NAME is not None:
                        attrib["service_name"] = SERVICE_NAME.group(1)
                attrib.update(attributes)
                dbl_quote = '"'
                printable_attributes = ",".join(
                    [f'{k}="{v.replace(dbl_quote, "_")}"' for k, v in attrib.items()]
                )
                result.append(f"{data.name}{{{printable_attributes}}} {value}")

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


class _Data(BaseProvider, Generic[Value]):
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
        return self.new_value()

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


class Inspect:
    """A class used to inspect a part ov code."""

    _start: float = 0

    def __init__(self, gauge: "Counter", tags: Dict[str, str], add_status: bool = False):
        self.gauge = gauge
        self.tags = tags
        self.add_status = add_status

    def __enter__(self) -> "_Inspect":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.end(exc_val is None)

    def __call__(self, function: Function) -> Function:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return function(*args, **kwargs)

        return wrapper

    def start(self) -> None:
        assert self.inspect_type is not None
        self._start = time.time()

    def end(self, success: bool = True, tags: Optional[Dict[str, str]] = None) -> None:
        assert self._start > 0
        self.gauge.get_value(tags).inc(
            {
                **({"status": "success" if success else "failure"} if self.add_status else {}),
                **self.tags,
                **(tags or {}),
            },
            time.time() - self._start,
            success,
        )


class GaugeValues(_Value):
    """The value store for a Prometheus gauge."""

    values: Dict[str, Union[int, float]] = {}
    start: float = 0

    def __init__(self, inspect_type: List[str] = None):
        self._start: float = 0
        self._inspect_type = inspect_type

    def get_values(self) -> Dict[str, Union[int, float]]:
        return values

    def inc(self, time, tags: Optional[Dict[str, str]] = None) -> None:
        assert self.inspect_type is not None
        for inspect_type in self.inspect_type:
            if inspect_type == "timer":
                self.values[inspect_type][success] = self.values.get(inspect_type, {}) + time
            if inspect_type == "counter":
                self.values[inspect_type][success] = self.values.get(inspect_type, {}) + 1


class Counter(_Data[GaugeValues]):
    """The provider interface."""

    def __init__(
        self,
        name: str,
        help_: str,
        extend: bool = True,
        inspect_type: List[str] = None,
        add_success: bool = False,
    ):
        self.name = name
        self.help = help_
        self.extend = extend
        self.inspect_type = inspect_type
        self.add_success = add_success
        super().__init__()

    def new_value(self) -> GaugeValues:
        return GaugeValues()

    def get_full_data(self) -> List[ProviderData]:
        result = []
        for inspect_type in self.inspect_type:
            result.append(
                {
                    name: self.name if len(self.inspect_type) == 1 else f"{self.name}_{inspect_type}",
                    help_: self.help if len(self.inspect_type) == 1 else f"{self.help} ({inspect_type})",
                    type_: "gauge",
                    extend: self.extend,
                    data: [
                        *[
                            ({"status": "success", **k}, v.get_values().get(inspect_type, {}).get(True, 0))
                            for k, v in self.data
                        ],
                        *[
                            ({"status": "failure", **k}, v.get_values().get(inspect_type, {}).get(False, 0))
                            for k, v in self.data
                        ],
                    ]
                    if self.add_success
                    else [
                        *[(k, v.get_values().get(inspect_type, {}).get(True, 0)) for k, v in self.data],
                        *[(k, v.get_values().get(inspect_type, {}).get(False, 0)) for k, v in self.data],
                    ],
                }
            )

    def inspect(self, tags: Dict[str, str] = {}) -> Inspect:
        return Inspect(self, tags)
