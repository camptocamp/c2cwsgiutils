from typing import List, Optional, Union  # noqa  # pylint: disable=unused-import

import pyramid.config
import pyramid.request
import pyramid.response

from c2cwsgiutils import config_utils, profiler
from c2cwsgiutils.auth import is_auth

additional_title: Optional[str] = None
additional_noauth: List[str] = []
additional_auth: List[str] = []
ELEM_ID = 0


def _url(request: pyramid.request.Request, route: str) -> Optional[str]:
    try:
        return request.route_url(route)  # type: ignore
    except KeyError:
        return None


def section(title: str, *content: str, sep: Optional[bool] = True) -> str:
    result = """
    <div class="row">
      <div class="col-sm-3"><h2>{title}</h2></div>
      <div class="col-lg">
      {content}
      </div>
    </div>
    """.format(
        title=title, content="\n".join(content)
    )
    if sep:
        result += "<hr>"
    return result


def paragraph(*content: str, title: Optional[str] = None) -> str:
    body = ""
    if title:
        body = title + ": "
    body += "\n".join(content)
    return "<p>" + body + "</p>"


def link(url: Optional[str], label: str) -> str:
    if url is not None:
        return '<a class="btn btn-primary" href="{url}" target="_blank">{label}</a>'.format(
            url=url, label=label
        )
    else:
        return ""


def form(url: Optional[str], *content: str, method: str = "get", target: str = "_blank") -> str:
    assert url is not None
    method_attrs = ""
    if method == "post":
        method_attrs = ' method="post" enctype="multipart/form-data"'
    return """
    <form class="form-inline" action="{url}" target="{target}"{method_attrs}>
      {content}
    </form>
    """.format(
        url=url, content="\n".join(content), method_attrs=method_attrs, target=target
    )


def input_(
    name: str, label: Optional[str] = None, type_: Optional[str] = None, value: Union[str, int] = ""
) -> str:
    global ELEM_ID
    id_ = ELEM_ID
    ELEM_ID += 1

    if label is None and type_ != "hidden":
        label = name
    if type_ is None:
        if isinstance(value, int):
            type_ = "number"
        else:
            type_ = "text"
    result = ""
    if label is not None:
        result += '<div class="form-group form-inline"><label for="{id}">{label}:</label>'.format(
            label=label, id=id_
        )
    result += '<input class="form-control" type="{type}" name="{name}" value="{value}" id="{id}">'.format(
        name=name, type=type_, value=value, id=id_
    )
    if label is not None:
        result += "</div>"
    return result


def button(label: str) -> str:
    return '<button class="btn btn-primary" type="submit">{label}</button>'.format(label=label)


def _index(request: pyramid.request.Request) -> pyramid.response.Response:
    response = request.response

    auth = is_auth(request)

    response.content_type = "text/html"
    response.text = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link rel="stylesheet"
              href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css"
              integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh"
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
            margin-bottom: 0.5rem;
          }
          hr {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
          }
          body {
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
        response.text += _db_maintenance(request)
        response.text += _logging(request)
        response.text += _profiler(request)

    if additional_title is not None and (auth or additional_noauth):
        response.text += additional_title
        response.text += "\n"

    if auth:
        response.text += "\n".join(additional_auth)
        response.text += "\n"

    response.text += "\n".join(additional_noauth)

    if not auth:
        auth_fields = [input_("secret", type_="password"), button("Login")]
    else:
        auth_fields = [input_("secret", type_="hidden"), button("Logout")]
    response.text += section(
        "Authentication",
        form(_url(request, "c2c_index"), *auth_fields, method="post", target="_self"),
        sep=False,
    )

    response.text += """
        </div>
      </body>
    </html>
    """
    return response


def _versions(request: pyramid.request.Request) -> str:
    versions_url = _url(request, "c2c_versions")
    if versions_url:
        return section("Versions", paragraph(link(versions_url, "Get")))
    else:
        return ""


def _stats(request: pyramid.request.Request) -> str:
    stats_url = _url(request, "c2c_read_stats_json")
    if stats_url:
        return section("Statistics", paragraph(link(stats_url, "Get")))
    else:
        return ""


def _profiler(request: pyramid.request.Request) -> str:
    sql_profiler_url = _url(request, "c2c_sql_profiler")
    if sql_profiler_url or profiler.PATH:
        result = ""

        if sql_profiler_url:
            result += paragraph(
                link(sql_profiler_url, "Status"),
                link(sql_profiler_url + "?enable=1", "Enable"),
                link(sql_profiler_url + "?enable=0", "Disable"),
                title="SQL",
            )

        if profiler.PATH:
            result += paragraph(link(profiler.PATH, "Profiler"), title="Python")
        return section("Profiler", result)
    else:
        return ""


def _db_maintenance(request: pyramid.request.Request) -> str:
    db_maintenance_url = _url(request, "c2c_db_maintenance")
    if db_maintenance_url:
        return section(
            "DB maintenance",
            paragraph(link(db_maintenance_url, "Get if readonly")),
            form(
                db_maintenance_url,
                button("Set readonly=true"),
                input_("readonly", value="true", type_="hidden"),
            ),
            form(
                db_maintenance_url,
                button("Set readonly=false"),
                input_("readonly", value="false", type_="hidden"),
            ),
        )
    else:
        return ""


def _logging(request: pyramid.request.Request) -> str:
    logging_url = _url(request, "c2c_logging_level")
    if logging_url:
        return section(
            "Logging",
            form(logging_url, button("Get"), input_("name", value="c2cwsgiutils")),
            form(
                logging_url,
                button("Set"),
                input_("name", value="c2cwsgiutils"),
                input_("level", value="INFO"),
            ),
            paragraph(link(logging_url, "List overrides")),
        )
    else:
        return ""


def _debug(request: pyramid.request.Request) -> str:
    dump_memory_url = _url(request, "c2c_debug_memory")
    if dump_memory_url:
        return section(
            "Debug",
            paragraph(
                link(_url(request, "c2c_debug_stacks"), "Stack traces"),
                link(_url(request, "c2c_debug_headers"), "HTTP headers"),
                link(_url(request, "c2c_debug_memory_maps"), "Mapped memory"),
            ),
            form(
                dump_memory_url,
                button("Dump memory usage"),
                input_("limit", value=30),
                input_("analyze_type"),
            ),
            form(
                _url(request, "c2c_debug_show_refs"),
                button("Object refs"),
                input_("analyze_type", value="gunicorn.app.wsgiapp.WSGIApplication"),
                input_("max_depth", value=3),
                input_("too_many", value=10),
                input_("min_size_kb", type_="number"),
            ),
            form(
                _url(request, "c2c_debug_memory_diff"),
                button("Memory diff"),
                input_("path"),
                input_("limit", value=30),
            ),
            form(_url(request, "c2c_debug_sleep"), button("Sleep"), input_("time", value=1)),
            form(_url(request, "c2c_debug_time"), button("Time")),
            form(
                _url(request, "c2c_debug_error"),
                button("Generate an HTTP error"),
                input_("status", value=500),
            ),
        )
    else:
        return ""


def _health_check(request: pyramid.request.Request) -> str:
    health_check_url = _url(request, "c2c_health_check")
    if health_check_url:
        return section(
            "Health checks",
            form(health_check_url, button("Run"), input_("max_level", value=1), input_("checks")),
        )
    else:
        return ""


def init(config: pyramid.config.Configurator) -> None:
    base_path = config_utils.get_base_path(config)
    if base_path != "":
        config.add_route("c2c_index", base_path, request_method=("GET", "POST"))
        config.add_view(_index, route_name="c2c_index", http_cache=0)
        config.add_route("c2c_index_slash", base_path + "/", request_method=("GET", "POST"))
        config.add_view(_index, route_name="c2c_index_slash", http_cache=0)
