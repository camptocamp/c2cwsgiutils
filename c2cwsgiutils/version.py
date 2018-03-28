import logging
import json
import os
import pyramid.config

from c2cwsgiutils import _utils

VERSIONS_PATH = '/app/versions.json'
LOG = logging.getLogger(__name__)


def init(config: pyramid.config.Configurator) -> None:
    if os.path.isfile(VERSIONS_PATH):
        with open(VERSIONS_PATH) as file:
            versions = json.load(file)
        config.add_route("c2c_versions", _utils.get_base_path(config) + r"/versions.json",
                         request_method="GET")
        config.add_view(lambda request: versions, route_name="c2c_versions", renderer="fast_json",
                        http_cache=0)
        LOG.info("Installed the /versions.json service")
        if 'git_tag' in versions['main']:
            LOG.warning("Starting version %s (%s)", versions['main']['git_tag'], versions['main']['git_hash'])
        else:
            LOG.warning("Starting version %s", versions['main']['git_hash'])
