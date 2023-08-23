import json
import logging
import os
import re
import warnings
from typing import Optional, cast

import prometheus_client
import pyramid.config

from c2cwsgiutils import config_utils, prometheus

_VERSIONS_PATH = "/app/versions.json"
_LOG = logging.getLogger(__name__)

_PACKAGES = os.environ.get("C2C_PROMETHEUS_PACKAGES", "c2cwsgiutils,pyramid,gunicorn,SQLAlchemy").split(",")
_APPLICATION_PACKAGES = os.environ.get("C2C_PROMETHEUS_APPLICATION_PACKAGE")
_LABEL_RE_NOT_ALLOWED = re.compile(r"[^a-zA-Z0-9]+")


def _sanitize_label(label: str) -> str:
    # Replace chart that nor a-zA-Z0-9 with _
    return _LABEL_RE_NOT_ALLOWED.sub("_", label)


_PROMETHEUS_VERSIONS_INFO = prometheus_client.Gauge(
    prometheus.build_metric_name("version"),
    "The version of the application",
    labelnames=[
        "git_hash",
        *[_sanitize_label(p) for p in _PACKAGES],
        *([] if _APPLICATION_PACKAGES is None else ["application"]),
    ],
    multiprocess_mode="liveall",
)


def init(config: pyramid.config.Configurator) -> None:
    """Initialize the versions view, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """Initialize the versions view."""

    if os.path.isfile(_VERSIONS_PATH):
        versions = _read_versions()
        config.add_route(
            "c2c_versions", config_utils.get_base_path(config) + r"/versions.json", request_method="GET"
        )
        config.add_view(
            lambda request: versions, route_name="c2c_versions", renderer="fast_json", http_cache=0
        )
        _LOG.info("Installed the /versions.json service")
        git_hash = versions["main"]["git_hash"]

        if "git_tag" in versions["main"]:
            _LOG.info("Starting version %s (%s)", versions["main"]["git_tag"], git_hash)
        else:
            _LOG.info("Starting version %s", git_hash)

        labels = {
            "git_hash": git_hash,
            **{
                _sanitize_label(package): versions["packages"].get(package, "<missing>")
                for package in _PACKAGES
            },
            **(
                {}
                if _APPLICATION_PACKAGES is None
                else {"application": versions["packages"].get(_APPLICATION_PACKAGES, "<missing>")}
            ),
        }
        _PROMETHEUS_VERSIONS_INFO.labels(**labels).set(1)


def _read_versions() -> dict[str, dict[str, str]]:
    """Read the version."""
    with open(_VERSIONS_PATH, encoding="utf-8") as file:
        versions = json.load(file)
    return cast(dict[str, dict[str, str]], versions)


def get_version() -> Optional[str]:
    """Get the version."""
    if not os.path.isfile(_VERSIONS_PATH):
        return None
    versions = _read_versions()
    return versions["main"]["git_hash"]
