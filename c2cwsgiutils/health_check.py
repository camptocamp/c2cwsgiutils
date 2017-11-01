"""
Setup an health_check API.

To use it, create an instance of this class in your application initialization and do a few calls to its
methods add_db_check()
"""
import configparser
import copy
import logging
import os
import pyramid.config
from pyramid.httpexceptions import HTTPNotFound
import pyramid.request
import re
import requests
import sqlalchemy.orm
import sqlalchemy.engine
import subprocess
import time
import traceback
from typing import Optional, Callable, Mapping, List, Tuple, Any

from c2cwsgiutils import stats, _utils

LOG = logging.getLogger(__name__)
ALEMBIC_HEAD_RE = re.compile(r'^([a-f0-9]+) \(head\)\n$')


def _get_bindings(session: Any) -> List[sqlalchemy.engine.Engine]:
    return [session.c2c_rw_bind, session.c2c_ro_bind] if session.c2c_rw_bind != session.c2c_ro_bind\
        else [session.c2c_rw_bind]


def _get_alembic_version(alembic_ini_path: str) -> str:
    # Go to the directory holding the config file and add '.' to the PYTHONPATH variable to support Alembic
    # migration scripts using common modules
    env = dict(os.environ)
    pythonpath = os.environ.get('PYTHONPATH', '')
    pythonpath = (pythonpath + ':' if pythonpath else '') + '.'
    env['PYTHONPATH'] = pythonpath

    out = subprocess.check_output(['alembic', '-c', alembic_ini_path, 'heads'],
                                  cwd=os.path.dirname(alembic_ini_path), env=env).decode('utf-8')
    out_match = ALEMBIC_HEAD_RE.match(out)
    if not out_match:
        raise Exception("Cannot get the alembic HEAD version from: " + out)
    return out_match.group(1)


class HealthCheck(object):
    def __init__(self, config: pyramid.config.Configurator) -> None:
        config.add_route("c2c_health_check", _utils.get_base_path(config) + r"/health_check",
                         request_method="GET")
        config.add_view(self._view, route_name="c2c_health_check", renderer="json", http_cache=0)
        self._checks = []  # type: List[Tuple[str, Callable[[pyramid.request.Request], None], int]]

    def add_db_session_check(self, session: sqlalchemy.orm.Session,
                             query_cb: Optional[Callable[[sqlalchemy.orm.Session], None]]=None,
                             at_least_one_model: Optional[object]=None, level: int=1) -> None:
        """
        Check a DB session is working. You can specify either query_cb or at_least_one_model.

        :param session: a DB session created by c2cwsgiutils.db.setup_session()
        :param query_cb: a callable that take a session as parameter and check it works
        :param at_least_one_model: a model that must have at least one entry in the DB
        :param level: the level of the health check
        """
        if query_cb is None:
            query_cb = self._at_least_one(at_least_one_model)
        for binding in _get_bindings(session):
            name, cb = self._create_db_engine_check(session, binding, query_cb)
            self._checks.append((name, cb, level))

    def add_alembic_check(self, session: sqlalchemy.orm.Session, alembic_ini_path: str, level: int=2) -> None:
        """
        Check the DB version against the HEAD version of Alembic.

        :param session: A DB session created by c2cwsgiutils.db.setup_session() giving access to the DB \
                        managed by Alembic
        :param alembic_ini_path: Path to the Alembic INI file.
        :param level: the level of the health check
        """
        def check(_request: Any) -> None:
            for binding in _get_bindings(session):
                prev_bind = session.bind
                try:
                    session.bind = binding
                    with stats.timer_context(['sql', 'manual', 'health_check',  'alembic', alembic_ini_path,
                                              binding.c2c_name]):
                        actual_version, = session.execute(
                            "SELECT version_num FROM {schema}.{table}".format(schema=schema, table=table)
                        ).fetchone()
                        if actual_version != version:
                            raise Exception("Invalid alembic version: %s != %s" % (actual_version, version))
                finally:
                    session.bind = prev_bind

        config = configparser.ConfigParser()
        config.read(alembic_ini_path)
        schema = config['alembic'].get('version_table_schema', 'public')
        table = config['alembic'].get('version_table', 'alembic_version')

        version = _get_alembic_version(alembic_ini_path)

        self._checks.append(('alembic_' + alembic_ini_path.replace('/', '_').strip('_'), check, level))

    def add_url_check(
            self, url: str, params: Optional[Mapping]=None, headers: Optional[Mapping]=None,
            name: Optional[str]=None,
            check_cb: Callable[[pyramid.request.Request, requests.Response], None]=lambda request,
            response: None, timeout: float=3, level: int=1) -> None:
        """
        Check that a GET on an URL returns 2xx

        :param url: the URL to query or a function taking the request and returning it
        :param params: the parameters or a function taking the request and returning them
        :param headers: the headers or a function taking the request and returning them
        :param name: the name of the check (defaults to url)
        :param check_cb: an optional CB to do additional checks on the response (takes the request and the \
                         response as parameters)
        :param timeout: the timeout
        :param level: the level of the health check
        """
        def check(request: pyramid.request.Request) -> None:
            the_url = _maybe_function(url, request)
            the_params = _maybe_function(params, request)
            the_headers = copy.deepcopy(_maybe_function(headers, request) if headers is not None else {})
            the_headers.update({
                'X-Request-ID': request.c2c_request_id
            })

            response = requests.get(the_url, timeout=timeout, params=the_params, headers=the_headers)
            response.raise_for_status()
            check_cb(request, response)
        if name is None:
            name = str(url)
        self._checks.append((name, check, level))

    def add_custom_check(self, name: str, check_cb: Callable[[pyramid.request.Request], None],
                         level: int=1) -> None:
        """
        Add a custom check

        :param name: the name of the check
        :param check_cb: the callback to call (takes the request as parameter)
        :param level: the level of the health check
        """
        self._checks.append((name, check_cb, level))

    def _view(self, request: pyramid.request.Request) -> Mapping[str, Any]:
        max_level = int(request.params.get('max_level', '1'))
        successes = []
        failures = {}
        timings = {}
        checks = None
        if 'checks' in request.params:
            checks = request.params['checks'].split(',')
        for name, check, level in self._checks:
            if level <= max_level and (checks is None or name in checks):
                start = time.monotonic()
                try:
                    check(request)
                    successes.append(name)
                except Exception as e:
                    LOG.warning("Health check %s failed", name, exc_info=True)
                    failure = {'message': str(e)}
                    if os.environ.get('DEVELOPMENT', '0') != '0':
                        failure['stacktrace'] = traceback.format_exc()
                    failures[name] = failure
                timings[name] = time.monotonic() - start

        if failures:
            request.response.status = 500

        return {
            'status': 500 if failures else 200,
            'failures': failures,
            'successes': successes,
            'timings': timings
        }

    @staticmethod
    def _create_db_engine_check(
            session: sqlalchemy.orm.Session,
            bind: sqlalchemy.engine.Engine,
            query_cb: Callable[[sqlalchemy.orm.Session], None]
    ) -> Tuple[str, Callable[[pyramid.request.Request], None]]:
        def check(_request: pyramid.request.Request) -> None:
            prev_bind = session.bind
            try:
                session.bind = bind
                with stats.timer_context(['sql', 'manual', 'health_check',  'db', bind.c2c_name]):
                    query_cb(session)
            finally:
                session.bind = prev_bind
        return 'db_engine_' + bind.c2c_name, check

    @staticmethod
    def _at_least_one(model: Any) -> Callable[[sqlalchemy.orm.Session], None]:
        def query(session: sqlalchemy.orm.Session) -> None:
            result = session.query(model).first()
            if result is None:
                raise HTTPNotFound(model.__name__ + " record not found")
        return query


def _maybe_function(what: Any, request: pyramid.request.Request) -> Any:
    return what(request) if callable(what) else what
