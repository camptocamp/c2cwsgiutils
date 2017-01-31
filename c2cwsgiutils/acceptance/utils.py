import logging
import netifaces
import os
import requests
import time

LOG = logging.getLogger(__name__)


def in_docker():
    return os.environ.get("DOCKER_RUN", "0") == "1"


DOCKER_GATEWAY = netifaces.gateways()[netifaces.AF_INET][0][0] if in_docker() else 'localhost'


def wait_url(url):
    def what():
        LOG.info("Trying to connect to " + url + "... ")
        r = requests.get(url)
        if r.status_code == 200:
            LOG.info(url + " service started")
            return True
        else:
            return False

    retry_timeout(what)


def retry_timeout(what, timeout=20, interval=0.5):
    timeout = time.time() + timeout
    while True:
        try:
            ret = what()
            if ret:
                return ret
        except Exception as e:
            LOG.info("  Failed: " + str(e))
        if time.time() > timeout:
            assert False, "Timeout"
        time.sleep(interval)
