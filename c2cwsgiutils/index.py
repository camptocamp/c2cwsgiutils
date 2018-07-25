import html
import pyramid.config
import pyramid.request
import pyramid.response
from typing import Optional
from urllib.parse import quote_plus

from . import _utils


def _url(request: pyramid.request.Request, route: str) -> Optional[str]:
    try:
        return request.route_url(route)
    except KeyError:
        return None


def _index(request: pyramid.request.Request) -> pyramid.response.Response:
    secret = request.params.get('secret')

    response = request.response
    response.content_type = 'text/html'
    response.text = """
    <html>
      <head>
      </head>
      <body>
    """

    if secret is None:
        response.text += """
        <form>
          secret: <input type="text" name="secret">
          <input type="submit" value="OK">
        </form>
        """

    response.text += _health_check(request)
    response.text += _stats(request)
    response.text += _versions(request)
    if secret is not None:
        response.text += _debug(request, secret)
        response.text += _logging(request, secret)
        response.text += _sql_profiler(request, secret)

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


def _sql_profiler(request: pyramid.request.Request, secret: str) -> str:
    sql_profiler_url = _url(request, 'c2c_sql_profiler')
    if sql_profiler_url:
        return """
        <h1>SQL profiler</h1>
        <a href="{url}?secret={secret}" target="_blank">status</a>
        <a href="{url}?secret={secret}&enable=1" target="_blank">enable</a>
        <a href="{url}?secret={secret}&enable=0" target="_blank">disable</a>
        """.format(url=sql_profiler_url, secret=quote_plus(secret))
    else:
        return ""


def _logging(request: pyramid.request.Request, secret: str) -> str:
    logging_url = _url(request, 'c2c_logging_level')
    if logging_url:
        return """
        <h1>Logging</h1>
        <ul>
          <li><form action="{logging_url}" target="_blank">
                <input type="submit" value="Get">
                name: <input type="text" name="name" value="c2cwsgiutils">
                <input type="hidden" name="secret" value="{secret}">
              </form></li>
          <li><form action="{logging_url}" target="_blank">
                <input type="submit" value="Set">
                name: <input type="text" name="name" value="c2cwsgiutils">
                level: <input type="text" name="level" value="INFO">
                <input type="hidden" name="secret" value="{secret}">
              </form></li>
        </ul>
        """.format(
            logging_url=logging_url,
            secret=html.escape(secret)
        )
    else:
        return ""


def _debug(request: pyramid.request.Request, secret: str) -> str:
    dump_memory_url = _url(request, 'c2c_debug_memory')
    if dump_memory_url:
        return """
        <h1>Debug</h1>
        <ul>
          <li><a href="{dump_stack_url}?secret={secret_url}" target="_blank">Stack traces</a></li>
          <li><form action="{dump_memory_url}" target="_blank">
                <input type="submit" value="Dump memory usage">
                limit: <input type="text" name="limit" value="30">
                <input type="hidden" name="secret" value="{secret_attr}">
              </form></li>
          <li><form action="{memory_diff_url}" target="_blank">
                <input type="submit" value="Memory diff">
                path: <input type="text" name="path">
                limit: <input type="text" name="limit" value="30">
                <input type="hidden" name="secret" value="{secret_attr}">
              </form></li>
          <li><form action="{sleep_url}" target="_blank">
                <input type="submit" value="Sleep">
                time: <input type="text" name="time" value="1">
                <input type="hidden" name="secret" value="{secret_attr}">
              </form></li>
          <li><a href="{dump_headers_url}?secret={secret_url}" target="_blank">HTTP headers</a></li>
          <li><form action="{error_url}" target="_blank">
                <input type="submit" value="Generate an HTTP error">
                status: <input type="text" name="status" value="500">
                <input type="hidden" name="secret" value="{secret_attr}">
              </form></li>
        </ul>
        """.format(
            dump_stack_url=_url(request, 'c2c_debug_stacks'),
            dump_memory_url=dump_memory_url,
            memory_diff_url=_url(request, 'c2c_debug_memory_diff'),
            sleep_url=_url(request, 'c2c_debug_sleep'),
            dump_headers_url=_url(request, 'c2c_debug_headers'),
            error_url=_url(request, 'c2c_debug_error'),
            secret_url=quote_plus(secret),
            secret_attr=html.escape(secret)
        )
    else:
        return ""


def _health_check(request: pyramid.request.Request) -> str:
    health_check_url = _url(request, 'c2c_health_check')
    if health_check_url:
        return """
        <h1>Health checks</h1>
        <form action="{url}" target="_blank">
          max_level: <input type="text" name="max_level" value="1">
          checks: <input type="text" name="checks" value="">
          <input type="submit" value="OK">
        </form>
        """.format(url=health_check_url)
    else:
        return ""


def init(config: pyramid.config.Configurator) -> None:
    base_path = _utils.get_base_path(config)
    if base_path != '':
        config.add_route("c2c_index", base_path, request_method="GET")
        config.add_view(_index, route_name="c2c_index", http_cache=0)
        config.add_route("c2c_index_slash", base_path + "/", request_method="GET")
        config.add_view(_index, route_name="c2c_index_slash", http_cache=0)
