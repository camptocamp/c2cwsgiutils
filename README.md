# Camptocamp WSGI utilities

This is a Python 3 library (>=3.5) providing common tools for Camptocamp WSGI
applications:

- Provide prometheus metrics
- Allow to use a master/slave PostgresQL configuration
- Logging handler for CEE/UDP logs
  - An optional view to change runtime the log levels
- SQL profiler to debug DB performance problems, disabled by default. Warning, it will slow down everything.
- A view to get the version information about the application and the installed packages
- A framework for implementing a health_check service
- Error handlers to send JSON messages to the client in case of error
- A cornice service drop in replacement for setting up CORS

Also provide tools for writing acceptance tests:

- A class that can be used from a py.test fixture to control a composition
- A class that can be used from a py.text fixture to test a REST API

As an example on how to use it in an application provided by a Docker image, you can look at the
test application in [acceptance_tests/app](acceptance_tests/app).
To see how to test such an application, look at [acceptance_tests/tests](acceptance_tests/tests).

## Install

### Custom Docker image (from PYPI library)

Here we didn't do a minimal install of c2cwsgiutils, but be put in place everything needed to
monitor the application in integration and production environment.

The library is available in PYPI:
[https://pypi.python.org/pypi/c2cwsgiutils](https://pypi.python.org/pypi/c2cwsgiutils)

Copy and adapt these template configuration file into your project:

- [production.ini](acceptance_tests/app/production.ini);
- [gunicorn.conf.py](acceptance_tests/app/gunicorn.conf.py).
  Then replace `c2cwsgiutils_app` by your package name.

You should install `c2cwsgiutils` with the tool you use to manage your pip dependencies.

In the `Dockerfile` you should add the following lines:

```dockerfile
# Generate the version file.
RUN c2cwsgiutils-genversion $(git rev-parse HEAD)

CMD ["gunicorn", "--paste=/app/production.ini"]

# Default values for the environment variables
ENV \
  DEVELOPMENT=0 \
  SQLALCHEMY_POOL_RECYCLE=30 \
  SQLALCHEMY_POOL_SIZE=5 \
  SQLALCHEMY_MAX_OVERFLOW=25 \
  SQLALCHEMY_SLAVE_POOL_RECYCLE=30 \
  SQLALCHEMY_SLAVE_POOL_SIZE=5 \
  SQLALCHEMY_SLAVE_MAX_OVERFLOW=25\
  LOG_TYPE=console \
  OTHER_LOG_LEVEL=WARNING \
  GUNICORN_LOG_LEVEL=WARNING \
  SQL_LOG_LEVEL=WARNING \
  C2CWSGIUTILS_LOG_LEVEL=WARNING \
  LOG_LEVEL=INFO
```

Add in your `main` function.

```python
config.include("c2cwsgiutils.pyramid")
dbsession = c2cwsgiutils.db.init(config, "sqlalchemy", "sqlalchemy_slave")

config.scan(...)

# Initialize the health checks
health_check = c2cwsgiutils.health_check.HealthCheck(config)
health_check.add_db_session_check(dbsession)
health_check.add_alembic_check(dbsession, "/app/alembic.ini", 1)
```

The related environment variables:

- `DEVELOPMENT`: set to `1` to enable the development mode, default is `0`.
- `SQLALCHEMY_URL`: SQL alchemy URL, like `postgresql://user:password@host:port/dbname`.
- `SQLALCHEMY_POOL_RECYCLE`: The SQL alchemy pool recycle, default is `30`.
- `SQLALCHEMY_POOL_SIZE`: The SQL alchemy pool size, default is `5`.
- `SQLALCHEMY_MAX_OVERFLOW`: SQL alchemy max overflow, default is `25`.
- `SQLALCHEMY_SLAVE_URL`: The SQL alchemy slave (read only) URL, like `postgresql://user:password@host:port/dbname`.
- `SQLALCHEMY_SLAVE_POOL_RECYCLE`: The SQL alchemy slave pool recycle, default is `30`.
- `SQLALCHEMY_SLAVE_POOL_SIZE`: The SQL alchemy slave pool size, default is `5`.
- `SQLALCHEMY_SLAVE_MAX_OVERFLOW`: The SQL alchemy slave max overflow, default is `25`.
- `GUNICORN_WORKERS`: The number of workers, default is `2`.
- `GUNICORN_THREADS`: The number of threads per worker, default is `10`.
- `LOG_TYPE`: The types of logs, default is `console`, should be `json` on kubernetes to work well with
  [elk](https://www.elastic.co/fr/what-is/elk-stack).
- `LOG_LEVEL`: The application log level, default is `INFO`.
- `SQL_LOG_LEVEL`: The SQL query log level, `WARNING`: no logs, `INFO`: logs the queries,
  `DEBUG` also logs the results, default is `WARNING`.
- `GUNICORN_ERROR_LOG_LEVEL`: The Gunicorn error log level, default is `WARNING`.
- `C2CWSGIUTILS_CONFIG`: The fallback ini file to use by gunicorn, default is `production.ini`.
- `C2CWSGIUTILS_LOG_LEVEL`: The c2c WSGI utils log level, default is `WARNING`.
- `OTHER_LOG_LEVEL`: The log level for all the other logger, default is `WARNING`.

Those environment variables can be useful for investigation on production environments.

### Docker (deprecated)

Or (deprecated) as a base Docker image:
[camptocamp/c2cwsgiutils:release_5](https://hub.docker.com/r/camptocamp/c2cwsgiutils/) or
[ghcr.io/camptocamp/c2cwsgiutils:release_5](https://github.com/orgs/camptocamp/packages/container/package/c2cwsgiutils)

If you need an image with a smaller foot print, use the tags prefixed with `-light`. Those are without
GDAL and without the build tools.

We deprecate the Docker image because:

- The project wants to choose the base image.
- The project pin different versions of the dependencies.

## General config

In general, configuration can be done both with environment variables (taken first) or with entries in the
`production.ini` file.

You can configure the base URL for accessing the views provided by c2cwsgiutils with an environment variable
named `C2C_BASE_PATH` or in the `production.ini` file with a property named `c2c.base_path`.

A few REST APIs are added and can be seen with this URL:
`{C2C_BASE_PATH}`.

Some APIs are protected by a secret. This secret is specified in the `C2C_SECRET` variable or `c2c.secret`
property. It is either passed as the `secret` query parameter or the `X-API-Key` header. Once
accessed with a good secret, a cookie is stored and the secret can be omitted.

An alternative of using `C2C_SECRET` is to use an authentication on GitHub,
[create the GitHub application](https://github.com/settings/applications/new).

Configure the json renderers with the `C2C_JSON_PRETTY_PRINT` and `C2C_JSON_SORT_KEYS` environment
variables or `c2c.json.pretty_print`and `c2c.json.sort_keys` properties. Default is `false`.

Then it will redirect the user to the github authentication form if not already authenticated
(using `C2C_AUTH_GITHUB_CLIENT_ID`, `C2C_AUTH_GITHUB_CLIENT_SECRET` and `C2C_AUTH_GITHUB_SCOPE`).

Then we will check if the user is allowed to access to the application, for that we check
if the user has enough right on a GitHub repository (using `C2C_AUTH_GITHUB_REPOSITORY`
and `C2C_AUTH_GITHUB_REPOSITORY_ACCESS_TYPE`).

Finally we store the session information in an encrypted cookie (using `C2C_AUTH_SECRET`
and `C2C_AUTH_COOKIE`).

Configuration details:

Using the environment variable `C2C_AUTH_GITHUB_REPOSITORY` or the config key `c2c.auth.github.repository`
to define the related GitHub repository (required).

Using the environment variable `C2C_AUTH_GITHUB_ACCESS_TYPE` or the config key
`c2c.auth.github.access_type` to define the type of required access can be `pull`, `push` or
`admin` (default is `push`)

Using the environment variable `C2C_AUTH_GITHUB_CLIENT_ID` or the config key `c2c.auth.github.client_id` to
define the GitHub application ID (required)

Using the environment variable `C2C_AUTH_GITHUB_CLIENT_SECRET` or the config key
`c2c.auth.github.client_secret` to define the GitHub application secret (required)

Using the environment variable `C2C_AUTH_GITHUB_SCOPE` or the config key `c2c.auth.github.scope` to define
the GitHub scope (default is `repo`), see [GitHub documentation](https://developer.github.com/apps/building-oauth-apps/understanding-scopes-for-oauth-apps/)

Using the environment variable `C2C_AUTH_GITHUB_SECRET` or the config key `c2c.auth.github.auth.secret` to
define the used secret for JWD encryption (required, with a length at least of 16)

Using the environment variable `C2C_AUTH_GITHUB_COOKIE` or the config key `c2c.auth.github.auth.cookie` to
define the used cookie name (default is `c2c-auth-jwt`)

Using the environment variable `C2C_AUTH_GITHUB_AUTH_URL` or the config key `c2c.auth.github.auth_url` to
define the GitHub auth URL (default is `https://github.com/login/oauth/authorize`)

Using the environment variable `C2C_AUTH_GITHUB_TOKEN_URL` or the config key `c2c.auth.github.token_url` to
define the GitHub auth URL (default is `https://github.com/login/oauth/access_token`)

Using the environment variable `C2C_AUTH_GITHUB_USER_URL` or the config key `c2c.auth.github.user_url` to
define the GitHub auth URL (default is `https://api.github.com/user`)

Using the environment variable `C2C_AUTH_GITHUB_REPO_URL` or the config key `c2c.auth.github.repo_url` to
define the GitHub auth URL (default is `https://api.github.com/repo`)

Using the environment variable `C2C_AUTH_GITHUB_PROXY_URL` or the config key `c2c.auth.github.auth.proxy_url` to
define a redirect proxy between GitHub and our application to be able to share an OAuth2 application on GitHub (default is no proxy).
Made to work with [this proxy](https://github.com/camptocamp/redirect/).

Using the environment variable `C2C_USE_SESSION` or the config key `c2c.use_session` to
define if we use a session. Currently, we can use the session to store a state, used to prevent CSRF, during OAuth2 login (default is `false`)

## Pyramid

All the environment variables are usable in the configuration file using stuff like `%(ENV_NAME)s`.

To enable most of the features of c2cwsgiutils, you need to add this line to your WSGI main:

```python
import c2cwsgiutils.pyramid
config.include(c2cwsgiutils.pyramid.includeme)
```

Error catching views will be put in place to return errors as JSON.

A custom loader is provided to run pyramid scripts against configuration files containing environment variables:

```shell
proutes c2c://production.ini      # relative path
proutes c2c:///app/production.ini # absolute path
```

A filter is automatically installed to handle the HTTP headers set by common proxies and have correct values
in the request object (`request.client_addr`, for example). This filter is equivalent to what the
`PasteDeploy#prefix` (minus the prefix part) does, but supports newer headers as well (`Forwarded`).
If you need to prefix your routes, you can use the `route_prefix` parameter of the `Configurator` constructor.

## Logging

Two new logging backends are provided:

- `c2cwsgiutils.pyramid_logging.PyramidCeeSysLogHandler`: to send @cee formatted logs to syslog through UDP.
- `c2cwsgiutils.pyramid_logging.JsonLogHandler`: to output (on stdout or stderr) JSON formatted logs.

Look at the logging configuration part of
[acceptance_tests/app/production.ini](acceptance_tests/app/production.ini) for paste and commands line.

The logging configuration is imported automatically by gunicorn, it is possible to visualize the dict config by setting the environment variable `DEBUG_LOGCONFIG=1`.

You can enable a view to configure the logging level on a live system using the `C2C_LOG_VIEW_ENABLED` environment
variable. Then, the current status of a logger can be queried with a GET on
`{C2C_BASE_PATH}/logging/level?secret={C2C_SECRET}&name={logger_name}` and can be changed with
`{C2C_BASE_PATH}/logging/level?secret={C2C_SECRET}&name={logger_name}&level={level}`. Overrides are stored in
Redis, if `C2C_REDIS_URL` (`c2c.redis_url`) or `C2C_REDIS_SENTINELS` is configured.

## Database maintenance

You can enable a view to force usage of the slave engine using the `C2C_DB_MAINTENANCE_VIEW_ENABLED` environment
variable. Then, the database can be made "readonly" with
`{C2C_BASE_PATH}/db/maintenance?secret={C2C_SECRET}&readonly=true`.
The current state is stored in Redis, if `C2C_REDIS_URL` (`c2c.redis_url`) or `C2C_REDIS_SENTINELS` is configured.

### Request tracking

In order to follow the logs generated by a request across all the services (think separate processes),
c2cwsgiutils tries to flag averything with a request ID. This field can come from the input as request headers
(`X-Request-ID`, `X-Correlation-ID`, `Request-ID` or `X-Varnish`) or will default to a UUID. You can add an
additional request header as source for that by defining the `C2C_REQUEST_ID_HEADER` environment variable
(`c2c.request_id_header`).

In JSON logging formats, a `request_id` field is automatically added.

You can enable (disabled by default since it can have a cost) the flagging of the SQL requests as well by
setting the C2C_SQL_REQUEST_ID environment variable (or c2c.sql_request_id in the .ini file). This will use
the application name to pass along the request id. If you do that, you must include the application name in
the PostgreSQL logs by setting `log_line_prefix` to something like `"%a "` (don't forget the space).

Then, in your application, it is recommended to transmit the request ID to the external REST APIs. Use
the `X-Request-ID` HTTP header, for example. The value of the request ID is accessible through an added
`c2c_request_id` attribute on the Pyramid Request objects. The `requests` module is patched to automatically
add this header.

The requests module is also patched to monitor requests done without timeout. In that case, you can
configure a default timeout with the `C2C_REQUESTS_DEFAULT_TIMEOUT` environment variable
(`c2c.requests_default_timeout`). If no timeout and no default is specified, a warning is issued.

## SQL profiler

The SQL profiler must be configured with the `C2C_SQL_PROFILER_ENABLED` environment variable. That enables a view
to query the status of the profiler (`{C2C_BASE_PATH}/sql_profiler?secret={C2C_SECRET}`) or to
enable/disable it (`{C2C_BASE_PATH}/sql_profiler?secret={C2C_SECRET}&enable={1|0}`).

If enabled, for each `SELECT` query sent by SQLAlchemy, another query it done with `EXPLAIN ANALYZE`
prepended to it. The results are sent to the `c2cwsgiutils.sql_profiler` logger.

Don't enable that on a busy production system. It will kill your performances.

## Profiler

C2cwsgiutils provide an easy way to profile an application:

With a decorator:

```python
from c2cwsgiutils.profile import Profiler

@Profile('/my_file.prof')
my_function():
    ...
```

Or with the `with` statement:

```python
from c2cwsgiutils.profile import Profiler

with Profile('/my_file.prof'):
    ...
```

Then open your file with SnakeViz:

```bash
docker cp container_name:/my_file.prof .
pip install --user snakeviz
snakeviz my_file.prof
```

## DB sessions

The `c2cwsgiutils.db.init` allows you to setup a DB session that has two engines for accessing a
master/slave PostgresQL setup. The slave engine (read only) will be used automatically for `GET` and `OPTIONS`
requests and the master engine (read write) will be used for the other queries.

To use that, your `production.ini` must look like that:

```ini
sqlalchemy.url = %(SQLALCHEMY_URL)s
sqlalchemy.pool_recycle = %(SQLALCHEMY_POOL_RECYCLE)s
sqlalchemy.pool_size = %(SQLALCHEMY_POOL_SIZE)s
sqlalchemy.max_overflow = %(SQLALCHEMY_MAX_OVERFLOW)s

sqlalchemy_slave.url = %(SQLALCHEMY_SLAVE_URL)s
sqlalchemy_slave.pool_recycle = %(SQLALCHEMY_SLAVE_POOL_RECYCLE)s
sqlalchemy_slave.pool_size = %(SQLALCHEMY_SLAVE_POOL_SIZE)s
sqlalchemy_slave.max_overflow = %(SQLALCHEMY_SLAVE_MAX_OVERFLOW)s
```

And your code that initializes the DB connection must look like that:

```python
import c2cwsgiutils.db

def main(config):
    c2cwsgiutils.db.init(config, 'sqlalchemy', 'sqlalchemy_slave', force_slave=[
        "POST /api/hello"
    ])[0]
```

You can use the `force_slave` and `force_master` parameters to override the defaults and force a route to use
the master or the slave engine.

## Health checks

To enable health checks, you must add some setup in your WSGI main (usually after the DB connections are
setup). For example:

```python
from c2cwsgiutils.health_check import HealthCheck

def custom_check(request):
    global not_happy
    if not_happy:
        raise Exception("I'm not happy")
    return "happy"

health_check = HealthCheck(config)
health_check.add_db_session_check(models.DBSession, at_least_one_model=models.Hello)
health_check.add_url_check('http://localhost:8080/api/hello')
health_check.add_custom_check('custom', custom_check, 2)
health_check.add_alembic_check(models.DBSession, '/app/alembic.ini', 3)
```

Then, the URL `{C2C_BASE_PATH}/health_check?max_level=3` can be used to run the health checks and get a report
looking like that (in case of error):

```json
{
  "status": 500,
  "successes": {
    "db_engine_sqlalchemy": { "timing": 0.002 },
    "db_engine_sqlalchemy_slave": { "timing": 0.003 },
    "http://localhost/api/hello": { "timing": 0.01 },
    "alembic_app_alembic.ini_alembic": { "timing": 0.005, "result": "4a8c1bb4e775" }
  },
  "failures": {
    "custom": {
      "message": "I'm not happy",
      "timing": 0.001
    }
  }
}
```

The levels are:

- 0: Don't add checks at this level. This max_level is used for doing a simple ping.
- 1: Checks for anything vital for the usefulness of the service (DB, redis, ...). This is the max_level set
  by default and used by load balancers to determine if the service is alive.
- \>=2: Use those at your convenience. Pingdom and CO are usually setup at max_level=100. So stay below.

The URL `{C2C_BASE_PATH}/health_check?checks=<check_name>` can be used to run the health checks on some
checks, coma separated list.

When you instantiate the `HealthCheck` class, two checks may be automatically enabled:

- If redis is configured, check that redis is reachable.
- If redis is configured and the version information is available, check that the version matches
  across all instances.

Look at the documentation of the `c2cwsgiutils.health_check.HealthCheck` class for more information.

## SQLAlchemy models graph

A command is provided that can generate Doxygen graphs of an SQLAlchemy ORM model.
See [acceptance_tests/app/models_graph.py](acceptance_tests/app/models_graph.py) how it's used.

## Version information

If the `/app/versions.json` exists, a view is added (`{C2C_BASE_PATH}/versions.json`) to query the current
version of a app. This file is generated by calling the `c2cwsgiutils-genversion [$GIT_TAG] $GIT_HASH`
command line. Usually done in the [Dockerfile](acceptance_tests/app/Dockerfile) of the WSGI application.

## Prometheus

[Prometheus client](https://github.com/prometheus/client_python) is integrated in c2cwsgiutils.

It will work in multi process mode with the limitation listed in the
[`prometheus_client` documentation](https://github.com/prometheus/client_python#multiprocess-mode-eg-gunicorn).

To enable it you should provide the `C2C_PROMETHEUS_PORT` environment variable.
For security reason, this port should not be exposed.

We can customize it with the following environment variables:

- `C2C_PROMETHEUS_PREFIX`: to customize the prefix, default is `c2cwsggiutils-`.
- `C2C_PROMETHEUS_PACKAGES` the packages that will be present in the version information, default is `c2cwsgiutils,pyramid,gunicorn,sqlalchemy`.
- `C2C_PROMETHEUS_APPLICATION_PACKAGE` the packages that will be present in the version information as application.

And you should add in your `gunicorn.conf.py`:

```python
from prometheus_client import multiprocess


def on_starting(server):
    from c2cwsgiutils import prometheus

    del server

    prometheus.start()


def post_fork(server, worker):
    from c2cwsgiutils import prometheus

    del server, worker

    prometheus.cleanup()


def child_exit(server, worker):
    del server

    multiprocess.mark_process_dead(worker.pid)
```

In your `Dockerfile` you should add:

```dockerfile
RUN mkdir -p /prometheus-metrics \
    && chmod a+rwx /prometheus-metrics
ENV PROMETHEUS_MULTIPROC_DIR=/prometheus-metrics
```

### Add custom metric collector

See [official documentation](https://github.com/prometheus/client_python#custom-collectors).

Related to the Unix process.

```python
from c2cwsgiutils import broadcast, prometheus

prometheus.MULTI_PROCESS_COLLECTOR_BROADCAST_CHANNELS.append("prometheus_collector_custom")
broadcast.subscribe("c2cwsgiutils_prometheus_collect_gc", _broadcast_collector_custom)
my_custom_collector_instance = MyCustomCollector()


def _broadcast_collector_custom() -> List[prometheus.SerializedGauge]:
    """Get the collected GC gauges."""

    return prometheus.serialize_collected_data(my_custom_collector_instance)
```

Related to the host, use that in the `gunicorn.conf.py`:

```python
def on_starting(server):
    from c2cwsgiutils import prometheus

    del server

    registry = CollectorRegistry()
    registry.register(MyCollector())
    prometheus.start(registry)
```

### Database metrics

Look at the `c2cwsgiutils-stats-db` utility if you want to generate statistics (gauges) about the
row counts.

### Usage of metrics

With c2cwsgiutils each instance (Pod) has its own metrics, so we need to aggregate them to have the metrics for the service you probably need to use `sum by (<fields>) (<metric>)` to get the metric (especially for counters).

## Custom scripts

To have the application initialized in a script you should use the
`c2cwsgiutils.setup_process.bootstrap_application_from_options` function.

Example of `main` function:

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="My scrypt.")
    # Add your argument here
    c2cwsgiutils.setup_process.fill_arguments(parser)
    args = parser.parse_args()
    env = c2cwsgiutils.setup_process.bootstrap_application_from_options(args)
    settings = env["registry"].settings

    # Add your code here
```

If you need an access to the database you should add:

```python
    engine = c2cwsgiutils.db.get_engine(settings)
    session_factory = c2cwsgiutils.db.get_session_factory(engine)
    with transaction.manager:
        # Add your code here
```

If you need the database connection without the application context, you can replace:

```python
    env = c2cwsgiutils.setup_process.bootstrap_application_from_options(args)
    settings = env["registry"].settings
```

by:

```python
    loader = pyramid.scripts.common.get_config_loader(args.config_uri)
    loader.setup_logging(parse_vars(args.config_vars) if args.config_vars else None)
    settings = loader.get_settings()
```

## Debugging

To enable the debugging interface, you must set the `C2C_DEBUG_VIEW_ENABLED` environment variable. Then you can
have dumps of a few things:

- every threads' stacktrace: `{C2C_BASE_PATH}/debug/stacks?secret={C2C_SECRET}`
- memory usage: `{C2C_BASE_PATH}/debug/memory?secret={C2C_SECRET}&limit=30&analyze_type=builtins.dict&python_internals_map=false`
- object ref: `{C2C_BASE_PATH}/debug/show_refs.dot?secret={C2C_SECRET}&analyze_type=gunicorn.app.wsgiapp.WSGIApplication&analyze_id=12345&max_depth=3&too_many=10&filter=1024&no_extra_info&backrefs`
  `analyze_type` and `analyze_id` should not ve used toogether, you can use it like:
  ```bash
  curl "<URL>" > /tmp/show_refs.dot
  dot -Lg -Tpng /tmp/show_refs.dot > /tmp/show_refs.png
  ```
- memory increase when calling another API: `{C2C_BASE_PATH}/debug/memory_diff?path={path_info}&secret={C2C_SECRET}&limit=30&no_warmup`
- sleep the given number of seconds (to test load balancer timeouts): `{C2C_BASE_PATH}/debug/sleep?secret={C2C_SECRET}&time=60.2`
- see the HTTP headers received by WSGI: `{C2C_BASE_PATH}/debug/headers?secret={C2C_SECRET}&status=500`
- return an HTTP error: `{C2C_BASE_PATH}/debug/error?secret={C2C_SECRET}&status=500`

To ease local development, the views are automatically reloaded when files change. In addition, the filesystem is mounted by the `docker-compose.override.yaml` file. Make sure not to use such file / mechanism in production.

### Broadcast

Some c2cwsgiutils APIs effect or query the state of the WSGI server. Since only one process out of the 5
(by default) time the number of servers gets a query, only this one will be affected. To avoid that, you
can configure c2cwsgiutils to use Redis pub/sub to broadcast those requests and collect the answers.

The impacted APIs are:

- `{C2C_BASE_PATH}/debug/stacks`
- `{C2C_BASE_PATH}/debug/memory`
- `{C2C_BASE_PATH}/logging/level`
- `{C2C_BASE_PATH}/sql_profiler`

The configuration parameters are:

- `C2C_REDIS_URL` (`c2c.redis_url`): The URL to the Redis single instance to use
- `C2C_REDIS_OPTIONS`: The Redis options, comma separated list of <key>=<value>, the value is parsed as YAML
- `C2C_REDIS_SENTINELS`: The coma separated list of Redis host:port sentinel instances to use
- `C2C_REDIS_SERVICENAME`: The redis service name in case of using sentinels
- `C2C_REDIS_DB`: The redis database number in case of using sentinels
- `C2C_BROADCAST_PREFIX` (`c2c.broadcast_prefix`): The prefix to add to the channels being used (must be
  different for 2 different services)

If not configured, only the process receiving the request is impacted.

## CORS

To have CORS compliant views, define your views like that:

```python
from c2cwsgiutils import services
hello_service = services.create("hello", "/hello", cors_credentials=True)

@hello_service.get()
def hello_get(request):
    return {'hello': True}
```

# Exception handling

c2cwsgiutils can install exception handling views that will catch any exception raised by the
application views and will transform it into a JSON response with a HTTP status corresponding to the error.

You can enable this by setting `C2C_ENABLE_EXCEPTION_HANDLING` (`c2c.enable_exception_handling`) to "1".

In development mode (`DEVELOPMENT=1`), all the details (SQL statement, stacktrace, ...) are sent to the
client. In production mode, you can still get them by sending the secret defined in `C2C_SECRET` in the query.

If you want to use pyramid_debugtoolbar, you need to disable exception handling and configure it like that:

```ini
pyramid.includes =
    pyramid_debugtoolbar
debugtoolbar.enabled = true
debugtoolbar.hosts = 0.0.0.0/0
debugtoolbar.intercept_exc = debug
debugtoolbar.show_on_exc_only = true
c2c.enable_exception_handling = 0
```

# JSON pretty print

Some JSON renderers are available:

- `json`: the normal JSON renderer (default).
- `fast_json`: a faster JSON renderer using ujson.
- `cornice_json`: the normal JSON renderer wrapped around cornice CorniceRenderer.
- `cornice_fast_json`: a faster JSON renderer wrapped around cornice CorniceRenderer.

Both pretty prints the rendered JSON. While this adds significant amount of whitespace, the difference in
bytes transmitted on the network is negligible thanks to gzip compression.

The `fast_json` renderer is using ujson which is faster, but doesn't offer the ability to change the rendering
of some types (the `default` parameter of json.dumps). This will interact badly with `papyrus` and such.

The cornice versions should be used to avoid the "'JSON' object has no attribute 'render_errors'" error.

## Sentry integration

The stacktraces can be sent to a sentry.io service for collection. To enable it, you must set the `SENTRY_URL`
(`c2c.sentry_url`) to point the the project's public DSN.

A few other environment variables can be used to tune the info sent with each report:

- `SENTRY_EXCLUDES` (`c2c.sentry.excludes`): list of loggers (colon separated, without spaces) to exclude for sentry
- `GIT_HASH` (`c2c.git_hash`): will be used for the release
- `SENTRY_CLIENT_RELEASE`: If not equal to "latest", will be taken for the release instead of the GIT_HASH
- `SENTRY_CLIENT_ENVIRONMENT`: the environment (dev, int, prod, ...)
- `SENTRY_CLIENT_IGNORE_EXCEPTIONS`: list (coma separated) of exceptions to ignore (defaults to SystemExit)
- `SENTRY_TAG_...`: to add other custom tags
- `SENTRY_LEVEL`: starting from what logging level to send events to Sentry (defaults to ERROR)
- `SENTRY_TRACES_SAMPLE_RATE`: The percentage of events to send to sentry in order to compute the performance. Value between 0 and 1, default is 0.

# Developer info

You will need `docker` (>=1.12.0), `docker-compose` (>=1.10.0) and
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

- bug fix version change: Nothing added, removed or changed in the API and only bug fix
  version number changes in the dependencies
- minor version change: The API must remain backward compatible and only minor version
  number changes in the dependencies
- major version change: The API and the dependencies are not backward compatible

To make a release:

- Change the the version in [setup.py](setup.py).
- Commit and push to master.
- Tag the GIT commit.
- Add the new branch name in the `.github/workflows/rebuild.yaml` and
  `.github/workflows/audit.yaml` files.

## Testing

### Screenshots

To test the screenshots, you need to install `node` with `npm`, to do that add the following lines in your `Dockerfile`:

```dockerfile
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get install --yes --no-install-recommends gnupg \
    && . /etc/os-release \
    && echo "deb https://deb.nodesource.com/node_18.x ${VERSION_CODENAME} main" > /etc/apt/sources.list.d/nodesource.list \
    && curl --silent https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - \
    && apt-get update \
    && apt-get install --assume-yes --no-install-recommends 'nodejs=18.*' \
        libx11-6 libx11-xcb1 libxcomposite1 libxcursor1 \
        libxdamage1 libxext6 libxi6 libxtst6 libnss3 libcups2 libxss1 libxrandr2 libasound2 libatk1.0-0 \
        libatk-bridge2.0-0 libpangocairo-1.0-0 libgtk-3.0 libxcb-dri3-0 libgbm1 libxshmfence1
```

To do the image test call `check_screenshot` e.g.:

```python
from c2cwsgiutils.acceptance import image

def test_screenshot(app_connection):
    image.check_screenshot(
        app_connection.base_url + "my-path",
        width=800,
        height=600,
        result_folder="results",
        expected_filename=os.path.join(os.path.dirname(__file__), "my-check.expected.png"),
    )
```

## Contributing

Install the pre-commit hooks:

```bash
pip install pre-commit
pre-commit install --allow-missing-config
```
