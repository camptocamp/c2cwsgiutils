import json
import logging
import os
import re
import warnings
from pathlib import Path
from typing import cast

import prometheus_client
import pyramid.config

from c2cwsgiutils import auth, config_utils, prometheus

_VERSIONS_PATH = Path("/app/versions.json")
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
    warnings.warn("init function is deprecated; use includeme instead", stacklevel=2)
    includeme(config)


class _View:
    def __init__(self, versions: dict[str, dict[str, str]]) -> None:
        self.versions = versions

    def __call__(self, request: pyramid.request.Request) -> dict[str, dict[str, str]]:
        auth.auth_view(request)
        return self.versions


def includeme(config: pyramid.config.Configurator) -> None:
    """Initialize the versions view."""
    if _VERSIONS_PATH.is_file():
        versions = _read_versions()
        config.add_route(
            "c2c_versions",
            config_utils.get_base_path(config) + r"/versions.json",
            request_method="GET",
        )
        config.add_view(_View(versions), route_name="c2c_versions", renderer="fast_json", http_cache=0)
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
    with _VERSIONS_PATH.open(encoding="utf-8") as file:
        versions = json.load(file)
    return cast("dict[str, dict[str, str]]", versions)


def get_version() -> str | None:
    """Get the version."""
    if not _VERSIONS_PATH.is_file():
        return None
    versions = _read_versions()
    return versions["main"]["git_hash"]
