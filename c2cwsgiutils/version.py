import logging
import json
import os

VERSIONS_PATH = '/app/versions.json'
LOG = logging.getLogger(__name__)


def init(config):
    if os.path.isfile(VERSIONS_PATH):
        with open(VERSIONS_PATH) as file:
            versions = json.load(file)
        config.add_route("c2c_versions", r"/versions.json", request_method="GET")
        config.add_view(lambda request: versions, route_name="c2c_versions", renderer="json", http_cache=0)
        LOG.info("Installed the /versions.json service")
