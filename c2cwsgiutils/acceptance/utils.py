import boltons.iterutils
import logging
import netifaces
import os
import pytest
import requests
import time
from typing import Callable, Any, Tuple

LOG = logging.getLogger(__name__)


def in_docker() -> bool:
    return os.environ.get("DOCKER_RUN", "0") == "1"


DOCKER_GATEWAY = netifaces.gateways()[netifaces.AF_INET][0][0] if in_docker() else 'localhost'
DEFAULT_TIMEOUT = 60


def wait_url(url: str, timeout: float=DEFAULT_TIMEOUT) -> None:
    def what() -> bool:
        LOG.info("Trying to connect to " + url + "... ")
        r = requests.get(url)
        if r.status_code == 200:
            LOG.info(url + " service started")
            return True
        else:
            return False

    retry_timeout(what, timeout=timeout)


def retry_timeout(what: Callable[[], Any], timeout: float=DEFAULT_TIMEOUT, interval: float=0.5) -> Any:
    timeout = time.monotonic() + timeout
    while True:
        try:
            ret = what()
            if ret:
                return ret
        except NameError:
            raise
        except Exception as e:
            LOG.info("  Failed: " + str(e))
        if time.monotonic() > timeout:
            assert False, "Timeout"
        time.sleep(interval)


skipIfCI = pytest.mark.skipif(os.environ.get('IN_CI', "0") == "1", reason="Not running on CI")


def approx(struct: Any, **kwargs: Any) -> Any:
    """
    Make float values in deep structures approximative. See pytest.approx
    """
    if isinstance(struct, float):
        return pytest.approx(struct, **kwargs)

    def visit(_path: list, key: Any, value: Any) -> Tuple[Any, Any]:
        if isinstance(value, float):
            value = pytest.approx(value, **kwargs)
        return key, value

    return boltons.iterutils.remap(struct, visit)
