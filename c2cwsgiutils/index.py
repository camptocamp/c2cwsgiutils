import pyramid.config
import pyramid.request
import pyramid.response
from typing import Optional, List  # noqa  # pylint: disable=unused-import
from c2cwsgiutils.auth import is_auth, get_expected_secret

from . import _utils

additional_title = None  # type: Optional[str]
additional_noauth = []  # type: List[str]
additional_auth = []  # type: List[str]


def _url(request: pyramid.request.Request, route: str) -> Optional[str]:
    try:
        return request.route_url(route)
    except KeyError:
        return None


def _index(request: pyramid.request.Request) -> pyramid.response.Response:
    response = request.response

    auth = is_auth(request)

    response.content_type = 'text/html'
    response.text = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link rel="stylesheet"
              href="https://stackpath.bootstrapcdn.com/bootstrap/4.2.1/css/bootstrap.min.css"
              integrity="sha384-GJzZqFGwb1QTTN6wy59ffF1BuGJpLSa9DkKMp0DgiMDm4iYMj70gZWKYbI706tWS"
              crossorigin="anonymous">
        <title>c2cwsgiutils tools</title>
        <style>
          form {
            margin-bottom: 1rem;
          }
          label {
            margin-right: 0.5rem;
          }
          input, button, a.btn {
            margin-right: 1rem;
          }
          div.col-lg {
            margin-top: 0.5rem;
          }
        </style>
      </head>
      <body>
        <div class="container-fluid">
    """

    response.text += _health_check(request)
    response.text += _stats(request)
    response.text += _versions(request)
    if auth:
        response.text += _debug(request)
        response.text += _logging(request)
        response.text += _sql_profiler(request)

    if additional_title is not None and (auth or len(additional_noauth) > 0):
        response.text += additional_title
        response.text += "\n"

    if auth:
        secret = get_expected_secret(request)
        response.text += "\n<hr>".join([e.format(
            # TODO: remove both for v3 (issue #177)
            secret=secret,
            secret_qs=("secret=" + secret) if secret is not None else "",
        ) for e in additional_auth])
        response.text += "\n"

    response.text += "\n<hr>".join(additional_noauth)

    response.text += """
        <div class="row">
          <div class="col-sm-3"><h2>Authentication</h2></div>
          <div class="col-lg">
    """
    if not auth:
        response.text += """
        <form class="form-inline">
          <label>secret:</label><input type="password" name="secret">
          <button class="btn btn-primary" type="submit">Login</button>
        </form>
        """
    else:
        response.text += """
        <form class="form-inline">
          <input type="hidden" name="secret" value="">
          <button class="btn btn-primary" type="submit">Logout</button>
        </form>
        """
    response.text += """
          </div>
        </div>
    """

    response.text += """
        </div>
      </body>
    </html>
    """
    return response


def _versions(request: pyramid.request.Request) -> str:
    versions_url = _url(request, 'c2c_versions')
    if versions_url:
        return """
        <div class="row">
          <div class="col-lg-3"><h2>Versions</h2></div>
          <div class="col-lg"><a class="btn btn-primary" href="{url}" target="_blank">Get</a></div>
        </div>
        <hr>
        """.format(url=versions_url)
    else:
        return ""


def _stats(request: pyramid.request.Request) -> str:
    stats_url = _url(request, 'c2c_read_stats_json')
    if stats_url:
        return """
        <div class="row">
          <div class="col-lg-3"><h2>Statistics</h2></div>
          <div class="col-lg"><a class="btn btn-primary" href="{url}" target="_blank">Get</a></div>
        </div>
        <hr>
        """.format(url=stats_url)
    else:
        return ""


def _sql_profiler(request: pyramid.request.Request) -> str:
    sql_profiler_url = _url(request, 'c2c_sql_profiler')
    if sql_profiler_url:
        return """
        <div class="row">
          <div class="col-lg-3"><h2>SQL profiler</h2></div>
          <div class="col-lg">
            <a class="btn btn-primary" href="{url}" target="_blank">Status</a>
            <a class="btn btn-primary" href="{url}?enable=1" target="_blank">Enable</a>
            <a class="btn btn-primary" href="{url}?enable=0" target="_blank">Disable</a>
          </div>
        </div>
        <hr>
        """.format(
            url=sql_profiler_url
        )
    else:
        return ""


def _logging(request: pyramid.request.Request) -> str:
    logging_url = _url(request, 'c2c_logging_level')
    if logging_url:
        return """
        <div class="row">
          <div class="col-lg-3"><h2>Logging</h2></div>
          <div class="col-lg">
            <form class="form-inline" action="{logging_url}" target="_blank">
              <button class="btn btn-primary" type="submit">Get</button>
              <label>name:</label><input class="form-control" type="text" name="name" value="c2cwsgiutils">
            </form>
            <form class="form-inline" action="{logging_url}" target="_blank">
              <button class="btn btn-primary" type="submit">Set</button>
              <label>name:</label><input class="form-control" type="text" name="name" value="c2cwsgiutils">
              <label>level:</label><input class="form-control" type="text" name="level" value="INFO">
            </form>
            <p><a href="{logging_url}" class="btn btn-primary" target="_blank">List overrides</a></p>
          </div>
        </div>
        <hr>
        """.format(
            logging_url=logging_url
        )
    else:
        return ""


def _debug(request: pyramid.request.Request) -> str:
    dump_memory_url = _url(request, 'c2c_debug_memory')
    if dump_memory_url:
        return """
        <div class="row">
          <div class="col-lg-3"><h2>Debug</h2></div>
          <div class="col-lg">
            <p>
              <a class="btn btn-primary" href="{dump_stack_url}" target="_blank">Stack traces</a>
              <a class="btn btn-primary" href="{dump_headers_url}" target="_blank">HTTP headers</a>
            </p>
            <form class="form-inline" action="{dump_memory_url}" target="_blank">
              <button class="btn btn-primary" type="submit">Dump memory usage</button>
              <label>limit:</label><input class="form-control" type="text" name="limit" value="30">
            </form>
            <form class="form-inline" action="{memory_diff_url}" target="_blank">
              <button class="btn btn-primary" type="submit">Memory diff</button>
              <label>path:</label><input class="form-control" type="text" name="path">
              <label>limit:</label><input class="form-control" type="text" name="limit" value="30">
            </form>
            <form class="form-inline" action="{sleep_url}" target="_blank">
              <button class="btn btn-primary" type="submit">Sleep</button>
              <label>time:</label><input class="form-control" type="text" name="time" value="1">
            </form>
            <form class="form-inline" action="{error_url}" target="_blank">
              <button class="btn btn-primary" type="submit">Generate an HTTP error</button>
              <label>status:</label><input class="form-control" type="text" name="status" value="500">
            </form>
          </div>
        </div>
        <hr>
        """.format(
            dump_stack_url=_url(request, 'c2c_debug_stacks'),
            dump_memory_url=dump_memory_url,
            memory_diff_url=_url(request, 'c2c_debug_memory_diff'),
            sleep_url=_url(request, 'c2c_debug_sleep'),
            dump_headers_url=_url(request, 'c2c_debug_headers'),
            error_url=_url(request, 'c2c_debug_error')
        )
    else:
        return ""


def _health_check(request: pyramid.request.Request) -> str:
    health_check_url = _url(request, 'c2c_health_check')
    if health_check_url:
        secret = request.params.get('secret')
        result = """
        <div class="row">
          <div class="col-lg-3"><h2>Health checks</h2></div>
          <div class="col-lg">
            <form class="form-inline" action="{url}" target="_blank">
              <button class="btn btn-primary" type="submit">Run</button>
              <label>max_level:</label><input class="form-control" type="text" name="max_level" value="1">
              <label>checks:</label> <input class="form-control" type="text" name="checks" value="">
        """.format(url=health_check_url)

        if secret is not None:
            result += '<input type="hidden" name="secret" value="%s">' % secret

        result += """
            </form>
          </div>
        </div>
        <hr>
        """
        return result
    else:
        return ""


def init(config: pyramid.config.Configurator) -> None:
    base_path = _utils.get_base_path(config)
    if base_path != '':
        config.add_route("c2c_index", base_path, request_method="GET")
        config.add_view(_index, route_name="c2c_index", http_cache=0)
        config.add_route("c2c_index_slash", base_path + "/", request_method="GET")
        config.add_view(_index, route_name="c2c_index_slash", http_cache=0)
