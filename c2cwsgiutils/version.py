import json
import logging
import os
from typing import Dict, Optional, cast

import pyramid.config

from c2cwsgiutils import config_utils, stats

VERSIONS_PATH = "/app/versions.json"
LOG = logging.getLogger(__name__)


def init(config: pyramid.config.Configurator) -> None:
    if os.path.isfile(VERSIONS_PATH):
        versions = _read_versions()
        config.add_route(
            "c2c_versions", config_utils.get_base_path(config) + r"/versions.json", request_method="GET"
        )
        config.add_view(
            lambda request: versions, route_name="c2c_versions", renderer="fast_json", http_cache=0
        )
        LOG.info("Installed the /versions.json service")
        git_hash = versions["main"]["git_hash"]

        if "git_tag" in versions["main"]:
            LOG.info("Starting version %s (%s)", versions["main"]["git_tag"], git_hash)
        else:
            LOG.info("Starting version %s", git_hash)

        if stats.USE_TAGS:
            stats.increment_counter(["version"], 1, tags=dict(version=git_hash))
        else:
            stats.increment_counter(["version", git_hash], 1)


def _read_versions() -> Dict[str, Dict[str, str]]:
    with open(VERSIONS_PATH) as file:
        versions = json.load(file)
    return cast(Dict[str, Dict[str, str]], versions)


def get_version() -> Optional[str]:
    if not os.path.isfile(VERSIONS_PATH):
        return None
    versions = _read_versions()
    return versions["main"]["git_hash"]
