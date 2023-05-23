import logging
import os
import subprocess  # nosec
import sys
import time
import warnings
from typing import Any, Callable, Dict, List, Mapping, Optional, cast

import netifaces
from pyramid.request import Request

from c2cwsgiutils.acceptance import utils

LOG = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="TEST: %(asctime)-15s %(levelname)5s %(name)s %(message)s",
    stream=sys.stdout,
)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARN)


def _try(what: Callable[[], Any], fail: bool = True, times: int = 5, delay: int = 10) -> Optional[Any]:
    for i in range(times):
        try:
            return what()
        except:  # pylint: disable=bare-except
            LOG.warning("Exception:", exc_info=True)
            if i + 1 == times and fail:
                raise
            time.sleep(delay)
    return None


class Composition:
    """The Docker composition."""

    def __init__(self, request: Request, composition: str, coverage_paths: Optional[str] = None) -> None:
        warnings.warn("The c2cwsgiutils.acceptance.composition should be used only if it's really needed.")
        self.cwd = os.path.dirname(composition)
        filename = os.path.basename(composition)
        self.docker_compose = ["docker-compose"]
        if filename != "docker-compose.yaml":
            self.docker_compose.append("--file=" + filename)
        self.coverage_paths = coverage_paths
        env = Composition._get_env()
        if os.environ.get("docker_start", "1") == "1":
            self.dc_try(["stop"], fail=False)
            self.dc_try(["rm", "-f"], fail=False)
            self.dc_try(["build"], fail=False)
            self.dc_try(["up", "-d"], fail=False)

        # Setup something that redirects the docker container logs to the test output
        log_watcher = subprocess.Popen(  # nosec, pylint: disable=consider-using-with
            self.docker_compose + ["logs", "--follow", "--no-color"],
            cwd=self.cwd,
            env=env,
            stderr=subprocess.STDOUT,
        )
        request.addfinalizer(log_watcher.kill)
        if os.environ.get("docker_stop", "1") == "1":
            request.addfinalizer(self.stop_all)

    def dc(self, args: List[str], **kwargs: Any) -> str:
        return cast(
            str,
            subprocess.run(  # nosec
                self.docker_compose + args,
                cwd=self.cwd,
                env=Composition._get_env(),
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
                check=True,
                **kwargs,
            ).stdout.decode(),
        )

    def dc_proc(self, args: List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        kwargs = {
            "cwd": self.cwd,
            "env": Composition._get_env(),
            **kwargs,
        }
        return subprocess.run(  # type: ignore[no-any-return, call-overload] # pylint: disable=subprocess-run-check # noqa
            self.docker_compose + args,
            **{"encoding": "utf-8", **kwargs},
        )  # nosec

    def dc_try(self, args: List[str], **kwargs: Any) -> None:
        _try(
            lambda: self.dc(args),
            **kwargs,
        )

    def stop_all(self) -> None:
        self.dc_try(["stop"])
        if self.coverage_paths:
            target_dir = "/reports/"
            os.makedirs(target_dir, exist_ok=True)
            for path in self.coverage_paths:
                try:
                    subprocess.check_call(  # nosec
                        ["docker", "cp", path, target_dir], stderr=subprocess.STDOUT
                    )
                except Exception:
                    self.dc(["ps"])
                    raise

    def stop(self, container: str) -> None:
        self.dc_try(["stop", container])

    def restart(self, container: str) -> None:
        self.dc_try(["restart", container])

    def run(self, container: str, *command: str, **kwargs: Dict[str, Any]) -> str:
        return self.dc(
            ["run", "--rm", container] + list(command),
            **kwargs,
        )

    def run_proc(
        self, container: str, *command: str, **kwargs: Dict[str, Any]
    ) -> subprocess.CompletedProcess[str]:
        return self.dc_proc(
            ["run", "--rm", container] + list(command),
            **kwargs,
        )

    def exec(self, container: str, *command: str, **kwargs: Dict[str, Any]) -> str:
        return self.dc(["exec", "-T", container] + list(command), **kwargs)

    @staticmethod
    def _get_env() -> Mapping[str, str]:
        """
        Make sure the DOCKER_TAG environment variable.

        Used in the docker-compose.yaml file is correctly set when we call docker-compose.
        """
        env = dict(os.environ)
        if "DOCKER_TAG" not in env:
            env["DOCKER_TAG"] = "latest"
        if utils.in_docker():
            env["DOCKER_IP"] = netifaces.gateways()[netifaces.AF_INET][0][0]
            env["DOCKER_CB_HOST"] = env["DOCKER_IP"]
        else:
            env["DOCKER_IP"] = netifaces.ifaddresses("docker0")[netifaces.AF_INET][0]["addr"]
            env["DOCKER_CB_HOST"] = "localhost"
        default_iface = netifaces.gateways()[netifaces.AF_INET][0][1]
        env["TEST_IP"] = netifaces.ifaddresses(default_iface)[netifaces.AF_INET][0]["addr"]
        return env
