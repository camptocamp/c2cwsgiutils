import logging
import json
import os
import pyramid.config
from typing import Optional, Any

from c2cwsgiutils import _utils

VERSIONS_PATH = '/app/versions.json'
LOG = logging.getLogger(__name__)


def init(config: pyramid.config.Configurator) -> None:
    if os.path.isfile(VERSIONS_PATH):
        versions = _read_versions()
        config.add_route("c2c_versions", _utils.get_base_path(config) + r"/versions.json",
                         request_method="GET")
        config.add_view(lambda request: versions, route_name="c2c_versions", renderer="fast_json",
                        http_cache=0)
        LOG.info("Installed the /versions.json service")
        if 'git_tag' in versions['main']:
            LOG.warning("Starting version %s (%s)", versions['main']['git_tag'], versions['main']['git_hash'])
        else:
            LOG.warning("Starting version %s", versions['main']['git_hash'])


def _read_versions() -> Any:
    with open(VERSIONS_PATH) as file:
        versions = json.load(file)
    return versions


def get_version() -> Optional[str]:
    if not os.path.isfile(VERSIONS_PATH):
        return None
    versions = _read_versions()
    return versions['main']['git_hash']
