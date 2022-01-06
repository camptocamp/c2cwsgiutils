import logging
import os
from typing import Dict, Set

LOG = logging.getLogger(__name__)


def get_config_defaults() -> Dict[str, str]:
    """
    Get the environment variables as defaults for configparser.

    configparser does not support duplicated defaults with different cases, this function filter
    the second one to avoid the issue.

    configparser interpretate the % then we need to escape them
    """
    result: Dict[str, str] = {}
    lowercase_keys: Set[str] = set()
    for key, value in os.environ.items():
        if key.lower() in lowercase_keys:
            LOG.warning("The environment variable '%s' is duplicated with different case, ignoring", key)
            continue
        lowercase_keys.add(key.lower())
        result[key] = value.replace("%", "%%")
    return result
