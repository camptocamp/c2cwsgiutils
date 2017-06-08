"""
Setup an health_check API.

To use it, create an instance of this class in your application initialization and do a few calls to its
methods add_db_check()
"""
import configparser
import logging
import os
from pyramid.httpexceptions import HTTPNotFound
import re
import requests
import subprocess
import traceback

from c2cwsgiutils import stats, _utils

LOG = logging.getLogger(__name__)
ALEMBIC_HEAD_RE = re.compile(r'^([a-f0-9]+) \(head\)\n$')


def _get_bindings(session):
    return [session.c2c_rw_bind, session.c2c_ro_bind] if session.c2c_rw_bind != session.c2c_ro_bind\
        else [session.c2c_rw_bind]


def _get_alembic_version(alembic_ini_path):
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


class HealthCheck:
    def __init__(self, config):
        config.add_route("c2c_health_check", _utils.get_base_path(config) + r"/health_check",
                         request_method="GET")
        config.add_view(self._view, route_name="c2c_health_check", renderer="json", http_cache=0)
        self._checks = []

    def add_db_session_check(self, session, query_cb=None, at_least_one_model=None, level=1):
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
            self._checks.append(self._create_db_engine_check(session, binding, query_cb) + (level,))

    def add_alembic_check(self, session, alembic_ini_path, level=2):
        """
        Check the DB version against the HEAD version of Alembic.

        :param session: A DB session created by c2cwsgiutils.db.setup_session() giving access to the DB \
                        managed by Alembic
        :param alembic_ini_path: Path to the Alembic INI file.
        :param level: the level of the health check
        """
        def check(_request):
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

    def add_url_check(self, url, name=None, check_cb=lambda request, response: None, timeout=3, level=1):
        """
        Check that a GET on an URL returns 2xx

        :param url: the URL to query
        :param name: the name of the check (defaults to url)
        :param check_cb: an optional CB to do additional checks on the response (takes the request and the \
                         response as parameters)
        :param timeout: the timeout
        :param level: the level of the health check
        """
        def check(request):
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            check_cb(request, response)
        if name is None:
            name = url
        self._checks.append((name, check, level))

    def add_custom_check(self, name, check_cb, level=1):
        """
        Add a custom check

        :param name: the name of the check
        :param check_cb: the callback to call (takes the request as parameter)
        :param level: the level of the health check
        """
        self._checks.append((name, check_cb, level))

    def _view(self, request):
        max_level = int(request.params.get('max_level', '1'))
        successes = []
        failures = {}
        for name, check, level in self._checks:
            if level <= max_level:
                try:
                    check(request)
                    successes.append(name)
                except Exception as e:
                    trace = traceback.format_exc()
                    LOG.error(trace)
                    failure = {'message': str(e)}
                    if os.environ.get('DEVELOPMENT', '0') != '0':
                        failure['stacktrace'] = trace
                    failures[name] = failure

        if failures:
            request.response.status = 500

        return {'status': 500 if failures else 200, 'failures': failures, 'successes': successes}

    def _create_db_engine_check(self, session, bind, query_cb):
        def check(request):
            prev_bind = session.bind
            try:
                session.bind = bind
                with stats.timer_context(['sql', 'manual', 'health_check',  'db', bind.c2c_name]):
                    query_cb(session)
            finally:
                session.bind = prev_bind
        return 'db_engine_' + bind.c2c_name, check

    def _at_least_one(self, model):
        def query(session):
            result = session.query(model).first()
            if result is None:
                raise HTTPNotFound(model.__name__ + " record not found")
        return query
