import logging
import os
from typing import Dict, Set

LOG = logging.getLogger(__name__)


def get_unique_env() -> Dict[str, str]:
    """
    Get the environment variables, with unique key case independent.

    configparser does not support duplicated defaults with different cases, this function filter
    the second one to avoid the issue.
    """
    result: Dict[str, str] = {}
    lowercase_keys: Set[str] = set()
    for key, value in os.environ.items():
        if key.lower() in lowercase_keys:
            LOG.warning("The environment variable '%s' is duplicated with different case, ignoring", key)
            continue
        lowercase_keys.add(key.lower())
        result[key] = value
    return result
