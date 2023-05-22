import logging
import urllib.parse
import warnings
from typing import Any, Dict, List, Optional, Union, cast

import jwt
import pyramid.config
import pyramid.request
import pyramid.response
from pyramid.httpexceptions import HTTPFound
from requests_oauthlib import OAuth2Session

from c2cwsgiutils import config_utils
from c2cwsgiutils.auth import (
    GITHUB_AUTH_COOKIE_ENV,
    GITHUB_AUTH_COOKIE_PROP,
    GITHUB_AUTH_PROXY_URL_ENV,
    GITHUB_AUTH_PROXY_URL_PROP,
    GITHUB_AUTH_SECRET_ENV,
    GITHUB_AUTH_SECRET_PROP,
    GITHUB_AUTH_URL_ENV,
    GITHUB_AUTH_URL_PROP,
    GITHUB_CLIENT_ID_ENV,
    GITHUB_CLIENT_ID_PROP,
    GITHUB_CLIENT_SECRET_ENV,
    GITHUB_CLIENT_SECRET_PROP,
    GITHUB_SCOPE_DEFAULT,
    GITHUB_SCOPE_ENV,
    GITHUB_SCOPE_PROP,
    GITHUB_TOKEN_URL_ENV,
    GITHUB_TOKEN_URL_PROP,
    GITHUB_USER_URL_ENV,
    GITHUB_USER_URL_PROP,
    SECRET_ENV,
    USE_SESSION_ENV,
    USE_SESSION_PROP,
    AuthenticationType,
    UserDetails,
    auth_type,
    check_access,
    is_auth_user,
)
from c2cwsgiutils.config_utils import env_or_settings

LOG = logging.getLogger(__name__)

additional_title: Optional[str] = None
additional_noauth: List[str] = []
additional_auth: List[str] = []
ELEM_ID = 0


def _url(
    request: pyramid.request.Request, route: str, params: Optional[Dict[str, str]] = None
) -> Optional[str]:
    try:
        return request.route_url(route, _query=params)  # type: ignore
    except KeyError:
        return None


def section(title: str, *content: str, sep: Optional[bool] = True) -> str:
    """Get an HTML section."""
    printable_content = "\n".join(content)
    result = f"""
    <div class="row">
      <div class="col-sm-3"><h2>{title}</h2></div>
      <div class="col-lg">
      {printable_content}
      </div>
    </div>
    """
    if sep:
        result += "<hr>"
    return result


def paragraph(*content: str, title: Optional[str] = None) -> str:
    """Get an HTML paragraph."""
    body = ""
    if title:
        body = title + ": "
    body += "\n".join(content)
    return "<p>" + body + "</p>"


def link(url: Optional[str], label: str, cssclass: str = "btn btn-primary", target: str = "_blank") -> str:
    """Get an HTML link."""
    attrs = ""
    if cssclass:
        attrs += f' class="{cssclass}"'
    if target:
        attrs += f' target="{target}"'
    if url is not None:
        return f'<a href="{url}"{attrs}>{label}</a>'
    else:
        return ""


def form(url: Optional[str], *content: str, method: str = "get", target: str = "_blank") -> str:
    """Get an HTML form."""
    assert url is not None
    method_attrs = ""
    if method == "post":
        method_attrs = ' method="post" enctype="multipart/form-data"'
    printable_content = "\n".join(content)
    return f"""
    <form class="form-inline" action="{url}" target="{target}"{method_attrs}>
      {printable_content}
    </form>
    """


def input_(
    name: str, label: Optional[str] = None, type_: Optional[str] = None, value: Union[str, int] = ""
) -> str:
    """Get an HTML input."""
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
        result += f'<div class="form-group form-inline"><label for="{id_}">{label}:</label>'
    result += f'<input class="form-control" type="{type_}" name="{name}" value="{value}" id="{id_}">'
    if label is not None:
        result += "</div>"
    return result


def button(label: str) -> str:
    """Get en HTML button."""
    return f'<button class="btn btn-primary" type="submit">{label}</button>'


def _index(request: pyramid.request.Request) -> pyramid.response.Response:
    response = request.response

    auth, user = is_auth_user(request)
    has_access = check_access(request)

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
    if has_access:
        response.text += _debug(request)
        response.text += _db_maintenance(request)
        response.text += _logging(request)
        response.text += _profiler(request)

    if additional_title is not None and (has_access or additional_noauth):
        response.text += additional_title
        response.text += "\n"

    if has_access:
        response.text += "\n".join(additional_auth)
        response.text += "\n"

    response.text += "\n".join(additional_noauth)

    settings = request.registry.settings
    auth_type_ = auth_type(settings)
    if auth_type_ == AuthenticationType.SECRET:
        if not auth:
            auth_fields = [input_("secret", type_="password"), button("Login")]
        else:
            auth_fields = [input_("secret", type_="hidden"), button("Logout")]
        response.text += section(
            "Authentication",
            form(_url(request, "c2c_index"), *auth_fields, method="post", target="_self"),
            sep=False,
        )
    elif not auth and auth_type_ == AuthenticationType.GITHUB:
        response.text += section(
            "Authentication",
            link(_url(request, "c2c_github_login"), "Login with GitHub", target=""),
            sep=False,
        )
    elif auth_type_ == AuthenticationType.GITHUB:
        response.text += section(
            "Authentication",
            f"Logged as: {link(user['url'], user['name'], cssclass='')}<br />"
            f"{link(_url(request, 'c2c_github_logout'), 'Logout', target='')}",
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
    if sql_profiler_url:
        result = ""

        if sql_profiler_url:
            result += paragraph(
                link(sql_profiler_url, "Status"),
                link(sql_profiler_url + "?enable=1", "Enable"),
                link(sql_profiler_url + "?enable=0", "Disable"),
                title="SQL",
            )

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


def _github_login(request: pyramid.request.Request) -> Dict[str, Any]:
    """Get the view that start the authentication on GitHub."""
    settings = request.registry.settings
    params = dict(request.params)
    callback_url = _url(
        request,
        "c2c_github_callback",
        {"came_from": params["came_from"]} if "came_from" in params else None,
    )
    proxy_url = env_or_settings(settings, GITHUB_AUTH_PROXY_URL_ENV, GITHUB_AUTH_PROXY_URL_PROP, "")
    if proxy_url:
        url = (
            proxy_url
            + ("&" if "?" in proxy_url else "?")
            + urllib.parse.urlencode({"came_from": callback_url})
        )
    else:
        url = callback_url
    oauth = OAuth2Session(
        env_or_settings(settings, GITHUB_CLIENT_ID_ENV, GITHUB_CLIENT_ID_PROP, ""),
        scope=[env_or_settings(settings, GITHUB_SCOPE_ENV, GITHUB_SCOPE_PROP, GITHUB_SCOPE_DEFAULT)],
        redirect_uri=url,
    )
    authorization_url, state = oauth.authorization_url(
        env_or_settings(
            settings, GITHUB_AUTH_URL_ENV, GITHUB_AUTH_URL_PROP, "https://github.com/login/oauth/authorize"
        ),
    )
    use_session = env_or_settings(settings, USE_SESSION_ENV, USE_SESSION_PROP, "").lower() == "true"
    # State is used to prevent CSRF, keep this for later.
    if use_session:
        request.session["oauth_state"] = state
    raise HTTPFound(location=authorization_url, headers=request.response.headers)


def _github_login_callback(request: pyramid.request.Request) -> Dict[str, Any]:
    """
    Do the post login operation authentication on GitHub.

    This will use the oauth token to get the user details from GitHub.
    And ask the GitHub rest API the information related to the configured repository
    to know witch kind of access the user have.
    """
    settings = request.registry.settings

    use_session = env_or_settings(settings, USE_SESSION_ENV, USE_SESSION_PROP, "").lower() == "true"
    state = request.session["oauth_state"] if use_session else None

    callback_url = _url(request, "c2c_github_callback")
    proxy_url = env_or_settings(settings, GITHUB_AUTH_PROXY_URL_ENV, GITHUB_AUTH_PROXY_URL_PROP, "")
    if proxy_url:
        url = (
            proxy_url
            + ("&" if "?" in proxy_url else "?")
            + urllib.parse.urlencode({"came_from": callback_url})
        )
    else:
        url = callback_url
    oauth = OAuth2Session(
        env_or_settings(settings, GITHUB_CLIENT_ID_ENV, GITHUB_CLIENT_ID_PROP, ""),
        scope=[env_or_settings(settings, GITHUB_SCOPE_ENV, GITHUB_SCOPE_PROP, GITHUB_SCOPE_DEFAULT)],
        redirect_uri=url,
        state=state,
    )

    if "error" in request.GET:
        return dict(request.GET)

    token = oauth.fetch_token(
        token_url=env_or_settings(
            settings,
            GITHUB_TOKEN_URL_ENV,
            GITHUB_TOKEN_URL_PROP,
            "https://github.com/login/oauth/access_token",
        ),
        authorization_response=request.current_route_url(_query=request.GET),
        client_secret=env_or_settings(settings, GITHUB_CLIENT_SECRET_ENV, GITHUB_CLIENT_SECRET_PROP, ""),
    )

    user = oauth.get(
        env_or_settings(
            settings,
            GITHUB_USER_URL_ENV,
            GITHUB_USER_URL_PROP,
            "https://api.github.com/user",
        )
    ).json()

    user_information: UserDetails = {
        "login": user["login"],
        "name": user["name"],
        "url": user["html_url"],
        "token": token,
    }
    request.response.set_cookie(
        env_or_settings(
            settings,
            GITHUB_AUTH_COOKIE_ENV,
            GITHUB_AUTH_COOKIE_PROP,
            "c2c-auth-jwt",
        ),
        jwt.encode(
            cast(Dict[str, Any], user_information),
            env_or_settings(
                settings,
                GITHUB_AUTH_SECRET_ENV,
                GITHUB_AUTH_SECRET_PROP,
            ),
            algorithm="HS256",
        ),
    )
    raise HTTPFound(
        location=request.params.get("came_from", _url(request, "c2c_index")),
        headers=request.response.headers,
    )


def _github_logout(request: pyramid.request.Request) -> Dict[str, Any]:
    """Logout the user."""
    request.response.delete_cookie(SECRET_ENV)
    request.response.delete_cookie(
        env_or_settings(
            request.registry.settings,
            GITHUB_AUTH_COOKIE_ENV,
            GITHUB_AUTH_COOKIE_PROP,
            "c2c-auth-jwt",
        ),
    )
    raise HTTPFound(
        location=request.params.get("came_from", _url(request, "c2c_index")), headers=request.response.headers
    )


def init(config: pyramid.config.Configurator) -> None:
    """Initialize the index page, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """Initialize the index page."""
    base_path = config_utils.get_base_path(config)
    if base_path != "":
        config.add_route("c2c_index", base_path, request_method=("GET", "POST"))
        config.add_view(_index, route_name="c2c_index", http_cache=0)
        config.add_route("c2c_index_slash", base_path + "/", request_method=("GET", "POST"))
        config.add_view(_index, route_name="c2c_index_slash", http_cache=0)

        settings = config.get_settings()
        auth_type_ = auth_type(settings)
        if auth_type_ == AuthenticationType.SECRET:
            LOG.warning(
                "It is recommended to use OAuth2 with GitHub login instead of the `C2C_SECRET` because it "
                "protects from brute force attacks and the access grant is personal and can be revoked."
            )

        if auth_type_ == AuthenticationType.GITHUB:
            config.add_route("c2c_github_login", base_path + "/github-login", request_method=("GET",))
            config.add_view(_github_login, route_name="c2c_github_login", http_cache=0)
            config.add_route("c2c_github_callback", base_path + "/github-callback", request_method=("GET",))
            config.add_view(
                _github_login_callback, route_name="c2c_github_callback", http_cache=0, renderer="fast_json"
            )
            config.add_route("c2c_github_logout", base_path + "/github-logout", request_method=("GET",))
            config.add_view(_github_logout, route_name="c2c_github_logout", http_cache=0)
