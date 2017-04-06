"""
A view (URL=/sql_provider) allowing to enabled/disable a SQL spy that runs an "EXPLAIN ANALYZE" on
every SELECT query going through SQLAlchemy.
"""
import logging
import os
from pyramid.httpexceptions import HTTPForbidden
import re
import sqlalchemy.event
import sqlalchemy.engine

from c2cwsgiutils import _utils

ENV_KEY = 'SQL_PROFILER_SECRET'
LOG = logging.getLogger(__name__)
enabled = False


def _sql_profiler_view(request):
    global enabled
    if request.params.get('secret') != os.environ[ENV_KEY]:
        raise HTTPForbidden('Missing or invalid secret parameter')
    if 'enable' in request.params:
        if request.params['enable'] == '1':
            if not enabled:
                LOG.warning("Enabling the SQL profiler")
                sqlalchemy.event.listen(sqlalchemy.engine.Engine, "before_cursor_execute",
                                        _before_cursor_execute)
                enabled = True
            return {'status': 200, 'enabled': True}
        else:
            if enabled:
                LOG.warning("Disabling the SQL profiler")
                sqlalchemy.event.remove(sqlalchemy.engine.Engine, "before_cursor_execute",
                                        _before_cursor_execute)
                enabled = False
            return {'status': 200, 'enabled': False}
    else:
        return {'status': 200, 'enabled': enabled}


def _beautify_sql(statement):
    statement = re.sub(r'SELECT [^\n]*\n', 'SELECT ...\n', statement)
    statement = re.sub(r' ((?:LEFT )?(?:OUTER )?JOIN )', r'\n\1', statement)
    statement = re.sub(r' ON ', r'\n  ON ', statement)
    statement = re.sub(r' GROUP BY ', r'\nGROUP BY ', statement)
    statement = re.sub(r' ORDER BY ', r'\nORDER BY ', statement)
    return statement


def _indent(statement, indent='  '):
    return indent + ("\n" + indent).join(statement.split('\n'))


def _before_cursor_execute(conn, _cursor, statement, parameters, _context, _executemany):
    if statement.startswith("SELECT ") and LOG.isEnabledFor(logging.INFO):
        try:
            output = "statement:\n%s\nparameters: %s\nplan:\n  " % (_indent(_beautify_sql(statement)),
                                                                    repr(parameters))
            output += '\n  '.join([row[0] for row in conn.engine.execute("EXPLAIN ANALYZE " + statement,
                                                                         parameters)])
            LOG.info(output)
        except:
            pass


def init(config):
    """
    Install a pyramid  event handler that adds the request information
    """
    if 'SQL_PROFILER_SECRET' in os.environ:
        config.add_route("c2c_sql_profiler", _utils.get_base_path(config) + r"/sql_profiler",
                         request_method="GET")
        config.add_view(_sql_profiler_view, route_name="c2c_sql_profiler", renderer="json", http_cache=0)
        LOG.info("Enabled the /sql_profiler API")
