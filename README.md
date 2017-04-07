Camptocamp WSGI utilities
=========================

This is a python 3 library providing common tools for Camptocamp WSGI
applications:

* Provide a small framework for gathering performance statistics about
  a web application (statsd protocol)
* Allow to use a master/slave PostgresQL configuration
* Logging handler for CEE/UDP logs
  * An optional (enabled by setting the LOG_VIEW_SECRET env var) view (/logging/level)
    to change runtime the log levels
* SQL profiler to debug DB performance problems, disabled by default. You must enable it by setting the
  SQL_PROFILER_SECRET env var and using the view (/sql_profiler) to switch it ON and OFF. Warning,
  it will slow down everything.
* A view to get the version information about the application and the installed packages (/versions.json)
* A framework for implementing a health_check service (/health_check)
* Error handlers to send JSON messages to the client in case of error
* A cornice service drop in replacement for setting up CORS

Also provide tools for writing acceptance tests:

* A class that can be used from a py.test fixture to control a
  composition
* A class that can be used from a py.text fixture to test a REST API

As an example on how to use it in an application provided by a Docker image, you can look at the
test application in [acceptance_tests/app](acceptance_tests/app).
To see how to test such an application, look at [acceptance_tests/tests](acceptance_tests/tests).


Install
-------

The library is available in PYPI:
[https://pypi.python.org/pypi/c2cwsgiutils](https://pypi.python.org/pypi/c2cwsgiutils)

With pip:
```
pip install c2cwsgiutils
```


General config
--------------

In general, configuration can be done both with environment variables (taken first) or with entries in the
`production.ini` file.

You can configure the base URL for accessing the views provided by c2cwsgiutils with an environment variable
named `C2C_BASE_PATH` or in the `production.ini` file with a property named `c2c.base_path`. 


Pyramid
-------

A command line (`c2cwsgiutils_run`) is provided to start an HTTP server (gunicorn) with a WSGI application.
By default, it will load the application configured in `/app/production.ini`, but you can change that with
the `C2CWSGIUTILS_CONFIG` environment variable. All the environment variables are usable in the configuration
file using stuff like `%(ENV_NAME)s`.

To enable most of the features of c2cwsgiutils, you need to add this line to you WSGI main:

```python
import c2cwsgiutils.pyramid
config.include(c2cwsgiutils.pyramid.includeme)
```

Error catching views will be put in place to return errors as JSON.


Logging
-------

A logging backend is provided to send @cee formatted logs to syslog through UDP.
Look at the logging configuration part of
[acceptance_tests/app/production.ini](acceptance_tests/app/production.ini) for a usage example.

You can enable a view to configure the logging level on a live system using the `LOG_VIEW_SECRET` environment
variable. Then, the current status of a logger can be queried with a GET on
`{C2C_BASE_PATH}/logging/level?secret={LOG_VIEW_SECRET}&name={logger_name}` and can be changed with
`{C2C_BASE_PATH}/logging/level?secret={LOG_VIEW_SECRET}&name={logger_name}&level={level}`


Metrics
-------

To enable and configure the metrics framework, you can use:

* STATS_VIEW (c2c.stats_view): if defined, will enable the stats view `{C2C_BASE_PATH}/stats.json`
* STATSD_ADDRESS (c2c.statsd_address): if defined, send stats to the given statsd server
* STATSD_PREFIX (c2c.statsd_prefix): prefix to add to every metric names

If enabled, some metrics are automatically generated:

* {STATSD_PREFIX}.route.{verb}.{route_name}.{status}: The time to process a query (includes rendering)
* {STATSD_PREFIX}.render.{verb}.{route_name}.{status}: The time to render a query
* {STATSD_PREFIX}.sql.{query}: The time to execute the given SQL query (simplified and normalized)

You can manually measure the time spent on something like that:

```python
from c2cwsgiutils import stats
with stats.timer_context('toto', 'tutu'):
    do_something()
```

Other functions exists to generate metrics. Look at the `c2cwsgiutils.stats` module.


SQL profiler
------------

The SQL profiler must be configured with the `SQL_PROFILER_SECRET` environment variable. That enables a view
to query the status of the profiler (`{C2C_BASE_PATH}/sql_profiler?secret={SQL_PROFILER_SECRET}`) or to
enable/disable it (`{C2C_BASE_PATH}/sql_profiler?secret={SQL_PROFILER_SECRET}&enable={1|0}`).

If enabled, for each `SELECT` query sent by SQLAlchemy, another query it done with `EXPLAIN ANALYZE`
prepended to it. The results are sent to the `c2cwsgiutils.sql_profiler` logger.

Don't enable that on a busy production system. It will kill your performances.


DB sessions
-----------

The `c2cwsgiutils.db.setup_session` allows you to setup a DB session that has two engines for accessing a
master/slave PostgresQL setup. The slave engine (read only) will be used automatically for `GET` and `OPTIONS`
requests and the master engine (read write) will be used for the other queries.

To use that, your production.ini must look like that:

```ini
sqlalchemy.url = %(SQLALCHEMY_URL)s
sqlalchemy.pool_recycle = 30
sqlalchemy.pool_size = 5
sqlalchemy.max_overflow = 25

sqlalchemy_slave.url = %(SQLALCHEMY_URL_SLAVE)s
sqlalchemy_slave.pool_recycle = 30
sqlalchemy_slave.pool_size = 5
sqlalchemy_slave.max_overflow = 25
```

And your code that initializes the DB connection must look like that:

```python
from c2cwsgiutils.db import setup_session
def init(config):
    global DBSession
    DBSession = setup_session(config, 'sqlalchemy', 'sqlalchemy_slave', force_slave=[
        "POST /api/hello"
    ])[0]
```

You can use the `force_slave` and `force_master` parameters to override the defaults and force a route to use
the master or the slave engine.


Health checks
-------------

To enable health checks, you must add some setup in your WSGI main (usually after the DB connections are
setup). For example:

```python
from c2cwsgiutils.health_check import HealthCheck

def custom_check(request):
    global not_happy
    if not_happy:
        raise Exception("I'm not happy")

health_check = HealthCheck(config)
health_check.add_db_session_check(models.DBSession, at_least_one_model=models.Hello)
health_check.add_url_check('http://localhost/api/hello')
health_check.add_custom_check('custom', custom_check, 2)
```

Then, the URL `{C2C_BASE_PATH}/health_check?max_level=2` can be used to run the health checks and get a report
looking like that (in case of error):

```json
{
    "status": 500,
    "successes": ["db_engine_sqlalchemy", "db_engine_sqlalchemy_slave", "http://localhost/api/hello"],
    "failures": {
        "custom": {
            "message": "I'm not happy"
        }
    }
}
```


SQLAlchemy models graph
-----------------------

A command is provided that can generate Doxygen graphs of an SQLAlchemy ORM model.
See [acceptance_tests/app/models_graph.py](acceptance_tests/app/models_graph.py) how it's used.


Version information
-------------------

If the `/app/versions.json` exists, a view is added (`{C2C_BASE_PATH}/version.json`) to query the current
version of a app. This file is generated by calling the `c2cwsgiutils_genversion.py $GIT_TAG $GIT_HASH`
command line. Usually done in the [Dockerfile](acceptance_tests/app/Dockerfile) of the WSGI application.


CORS
----

To have CORS compliant views, define your views like that:

```python
from c2cwsgiutils import services
hello_service = services.create("hello", "/hello", cors_credentials=True)

@hello_service.get()
def hello_get(request):
    return {'hello': True}
```


Developer info
==============

You will need `docker` (>=1.12.0), `docker-compose` (>=1.10.0), twine and
`make` installed on the machine to play with this project.
Check available versions of `docker-engine` with
`apt-get policy docker-engine` and eventually force install the
up-to-date version using a command similar to
`apt-get install docker-engine=1.12.3-0~xenial`.

To lint and test everything, run the following command:

```shell
make
```

Make sure you are strict with the version numbers:

* bug fix version change: Nothing added, removed or changed in the API and only bug fix
  version number changes in the dependencies
* minor version change: The API must remain backward compatible and only minor version
  number changes in the dependencies
* major version change: The API and the dependencies are not backward compatible

To make a release:

* Change the the version in [setup.py](setup.py)
* run `make release`
