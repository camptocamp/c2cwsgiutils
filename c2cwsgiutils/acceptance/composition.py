import logging
import netifaces
import os
import _pytest.fixtures
import subprocess
import sys
import time
from typing import Callable, Any, Optional, List, Mapping

from c2cwsgiutils.acceptance import utils

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format="TEST       | %(asctime)-15s %(levelname)5s %(name)s %(message)s",
                    stream=sys.stdout)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARN)


def _try(what: Callable[[], Any], fail: bool=True, times: int=5, delay: float=10) -> Any:
    for i in range(times):
        # noinspection PyBroadException
        try:
            return what()
        except Exception:
            LOG.warning("Exception:", exc_info=True)
            if i+1 == times and fail:
                raise
            time.sleep(delay)


class Composition(object):
    def __init__(self, request: _pytest.fixtures.FixtureRequest, project_name: str, composition: str,
                 coverage_paths: Optional[List[str]]=None) -> None:
        self.project_name = project_name
        self.composition_file = composition
        self.coverage_paths = coverage_paths
        env = Composition._get_env()
        if os.environ.get("docker_start", "1") == "1":
            _try(lambda:
                 subprocess.check_call(['docker-compose', '--file', composition,
                                        '--project-name', project_name, 'stop'], env=env,
                                       stderr=subprocess.STDOUT), fail=False)

            _try(lambda:
                 subprocess.check_call(['docker-compose', '--file', composition,
                                        '--project-name', project_name, 'rm', '-f', '-v'], env=env,
                                       stderr=subprocess.STDOUT), fail=False)

            _try(lambda:
                 subprocess.check_call(['docker-compose', '--file', composition,
                                       '--project-name', project_name, 'build'], env=env,
                                       stderr=subprocess.STDOUT), fail=False)

            _try(lambda:
                 subprocess.check_call(['docker-compose', '--file', composition,
                                       '--project-name', project_name, 'up', '-d'], env=env,
                                       stderr=subprocess.STDOUT))

        # setup something that redirects the docker container logs to the test output
        log_watcher = subprocess.Popen(['docker-compose', '--file', composition,
                                       '--project-name', project_name, 'logs', '--follow', '--no-color'],
                                       env=env, stderr=subprocess.STDOUT)
        request.addfinalizer(log_watcher.kill)
        if os.environ.get("docker_stop", "1") == "1":
            request.addfinalizer(self.stop_all)

    def stop_all(self) -> None:
        env = Composition._get_env()
        _try(lambda:
             subprocess.check_call(['docker-compose', '--file', self.composition_file,
                                   '--project-name', self.project_name, 'stop'], env=env,
                                   stderr=subprocess.STDOUT))
        if self.coverage_paths:
            target_dir = "/reports/"
            os.makedirs(target_dir, exist_ok=True)
            for path in self.coverage_paths:
                subprocess.check_call(['docker', 'cp', path, target_dir], stderr=subprocess.STDOUT)

        _try(lambda:
             subprocess.check_call(['docker-compose', '--file', self.composition_file,
                                    '--project-name', self.project_name, 'rm', '-f', '-v'], env=env,
                                   stderr=subprocess.STDOUT), fail=False)

    def stop(self, container: str) -> None:
        _try(lambda:
             subprocess.check_call(['docker', '--log-level=warn',
                                   'stop', '%s_%s_1' % (self.project_name, container)],
                                   stderr=subprocess.STDOUT))

    def restart(self, container: str) -> None:
        _try(lambda:
             subprocess.check_call(['docker', '--log-level=warn',
                                   'restart', '%s_%s_1' % (self.project_name, container)],
                                   stderr=subprocess.STDOUT))

    def run(self, container: str, *command: str, **kwargs: Any) -> None:
        subprocess.check_call(['docker-compose', '--file', self.composition_file,
                               '--project-name', self.project_name, 'run', '--rm', container] + list(command),
                              env=Composition._get_env(), stderr=subprocess.STDOUT, **kwargs)

    def exec(self, container: str, *command: str, **kwargs: Any) -> None:
        subprocess.check_call(['docker-compose', '--file', self.composition_file,
                               '--project-name', self.project_name, 'exec', '-T', container] + list(command),
                              env=Composition._get_env(), stderr=subprocess.STDOUT, **kwargs)

    @staticmethod
    def _get_env() -> Mapping[str, str]:
        """
        Make sure the DOCKER_TAG environment variable, used in the docker-compose.yml file
        is correctly set when we call docker-compose.
        """
        env = dict(os.environ)
        if 'DOCKER_TAG' not in env:
            env['DOCKER_TAG'] = 'latest'
        if utils.in_docker():
            env['DOCKER_IP'] = netifaces.gateways()[netifaces.AF_INET][0][0]
            env['DOCKER_CB_HOST'] = env['DOCKER_IP']
        else:
            env['DOCKER_IP'] = netifaces.ifaddresses('docker0')[netifaces.AF_INET][0]['addr']
            env['DOCKER_CB_HOST'] = 'localhost'
        default_iface = netifaces.gateways()[netifaces.AF_INET][0][1]
        env['TEST_IP'] = netifaces.ifaddresses(default_iface)[netifaces.AF_INET][0]['addr']
        return env
