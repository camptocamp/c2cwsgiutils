"""Used to publish metrics to Prometheus."""

import re
import socket
import warnings
from os import listdir
from typing import Any, Dict, List, Optional, Tuple, Union

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


def _metrics() -> pyramid.response.Response:
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
