import logging
import os
import time
from typing import Any, Callable, List, Tuple

import boltons.iterutils
import netifaces
import pytest
import requests

LOG = logging.getLogger(__name__)


def in_docker() -> bool:
    """Is in Docker mode."""
    return os.environ.get("DOCKER_RUN") != "0"


DOCKER_GATEWAY = netifaces.gateways()[netifaces.AF_INET][0][0] if in_docker() else "localhost"
DEFAULT_TIMEOUT = 60


def wait_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
    """Wait the the URL is available without any error."""

    def what() -> bool:
        LOG.info("Trying to connect to %s... ", url)
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            LOG.info("%s service started", url)
            return True
        else:
            return False

    retry_timeout(what, timeout=timeout)


def retry_timeout(what: Callable[[], Any], timeout: float = DEFAULT_TIMEOUT, interval: float = 0.5) -> Any:
    """
    Retry the function until the timeout.

    Arguments:

        what: the function to try
        timeout: the timeout to get a success
        interval: the interval between try
    """
    timeout = time.monotonic() + timeout
    while True:
        error = ""
        try:
            ret = what()
            if ret:
                return ret
        except NameError:
            raise
        except Exception as e:  # pylint: disable=broad-except
            error = str(e)
            LOG.info("  Failed: %s", e)
        if time.monotonic() > timeout:
            assert False, "Timeout: " + error
        time.sleep(interval)


def approx(struct: Any, **kwargs: Any) -> Any:
    """
    Make float values in deep structures approximative.

    See pytest.approx
    """
    if isinstance(struct, float):
        return pytest.approx(struct, **kwargs)

    def visit(_path: List[str], key: Any, value: Any) -> Tuple[Any, Any]:
        if isinstance(value, float):
            value = pytest.approx(value, **kwargs)
        return key, value

    return boltons.iterutils.remap(struct, visit)
