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
    <html>
      <head>
      </head>
      <body>
    """

    response.text += "<h1>Authentication</h1>"
    if not auth:
        response.text += """
        <form>
          secret: <input type="text" name="secret">
          <input type="submit" value="Login">
        </form>
        """
    else:
        response.text += """
        <form>
          <input type="hidden" name="secret" value="">
          <input type="submit" value="Logout">
        </form>
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
        response.text += "\n".join([e.format(
            # TODO: remove both for v3 (issue #177)
            secret=secret,
            secret_qs=("secret=" + secret) if secret is not None else "",
        ) for e in additional_auth])
        response.text += "\n"

    response.text += "\n".join(additional_noauth)
    response.text += """
      </body>
    </html>
    """
    return response


def _versions(request: pyramid.request.Request) -> str:
    versions_url = _url(request, 'c2c_versions')
    if versions_url:
        return """
        <h1>Versions</h1>
        <a href="{url}" target="_blank">get</a>
        """.format(url=versions_url)
    else:
        return ""


def _stats(request: pyramid.request.Request) -> str:
    stats_url = _url(request, 'c2c_read_stats_json')
    if stats_url:
        return """
        <h1>Statistics</h1>
        <a href="{url}" target="_blank">get</a>
        """.format(url=stats_url)
    else:
        return ""


def _sql_profiler(request: pyramid.request.Request) -> str:
    sql_profiler_url = _url(request, 'c2c_sql_profiler')
    if sql_profiler_url:
        return """
        <h1>SQL profiler</h1>
        <a href="{url}" target="_blank">status</a>
        <a href="{url}?enable=1" target="_blank">enable</a>
        <a href="{url}?enable=0" target="_blank">disable</a>
        """.format(
            url=sql_profiler_url
        )
    else:
        return ""


def _logging(request: pyramid.request.Request) -> str:
    logging_url = _url(request, 'c2c_logging_level')
    if logging_url:
        return """
        <h1>Logging</h1>
        <ul>
          <li><form action="{logging_url}" target="_blank">
                <input type="submit" value="Get">
                name: <input type="text" name="name" value="c2cwsgiutils">
              </form></li>
          <li><form action="{logging_url}" target="_blank">
                <input type="submit" value="Set">
                name: <input type="text" name="name" value="c2cwsgiutils">
                level: <input type="text" name="level" value="INFO">
              </form></li>
          <li><a href="{logging_url}" target="_blank">List overrides</a>
        </ul>
        """.format(
            logging_url=logging_url
        )
    else:
        return ""


def _debug(request: pyramid.request.Request) -> str:
    dump_memory_url = _url(request, 'c2c_debug_memory')
    if dump_memory_url:
        return """
        <h1>Debug</h1>
        <ul>
          <li><a href="{dump_stack_url}" target="_blank">Stack traces</a></li>
          <li><form action="{dump_memory_url}" target="_blank">
                <input type="submit" value="Dump memory usage">
                limit: <input type="text" name="limit" value="30">
              </form></li>
          <li><form action="{memory_diff_url}" target="_blank">
                <input type="submit" value="Memory diff">
                path: <input type="text" name="path">
                limit: <input type="text" name="limit" value="30">
              </form></li>
          <li><form action="{sleep_url}" target="_blank">
                <input type="submit" value="Sleep">
                time: <input type="text" name="time" value="1">
              </form></li>
          <li><a href="{dump_headers_url}" target="_blank">HTTP headers</a></li>
          <li><form action="{error_url}" target="_blank">
                <input type="submit" value="Generate an HTTP error">
                status: <input type="text" name="status" value="500">
              </form></li>
        </ul>
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
        <h1>Health checks</h1>
        <form action="{url}" target="_blank">
          max_level: <input type="text" name="max_level" value="1">
          checks: <input type="text" name="checks" value="">
        """.format(url=health_check_url)

        if secret is not None:
            result += '<input type="hidden" name="secret" value="%s">' % secret

        result += """
          <input type="submit" value="OK">
        </form>
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
