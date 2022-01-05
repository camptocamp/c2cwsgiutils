import hashlib
import logging
from enum import Enum
from typing import Any, Mapping, Optional, Tuple, TypedDict, cast

import jwt
import pyramid.request
from pyramid.httpexceptions import HTTPForbidden

from c2cwsgiutils.config_utils import config_bool, env_or_config, env_or_settings

COOKIE_AGE = 7 * 24 * 3600
SECRET_PROP = "c2c.secret"  # nosec  # noqa
SECRET_ENV = "C2C_SECRET"  # nosec  # noqa
GITHUB_REPOSITORY_PROP = "c2c.auth.github.repository"
GITHUB_REPOSITORY_ENV = "C2C_AUTH_GITHUB_REPOSITORY"
GITHUB_ACCESS_TYPE_PROP = "c2c.auth.github.access_type"
GITHUB_ACCESS_TYPE_ENV = "C2C_AUTH_GITHUB_ACCESS_TYPE"
GITHUB_AUTH_URL_PROP = "c2c.auth.github.auth_url"
GITHUB_AUTH_URL_ENV = "C2C_AUTH_GITHUB_AUTH_URL"
GITHUB_TOKEN_URL_PROP = "c2c.auth.github.token_url"  # nosec
GITHUB_TOKEN_URL_ENV = "C2C_AUTH_GITHUB_TOKEN_URL"  # nosec
GITHUB_USER_URL_PROP = "c2c.auth.github.user_url"
GITHUB_USER_URL_ENV = "C2C_AUTH_GITHUB_USER_URL"
GITHUB_REPO_URL_PROP = "c2c.auth.github.repo_url"
GITHUB_REPO_URL_ENV = "C2C_AUTH_GITHUB_REPO_URL"
GITHUB_CLIENT_ID_PROP = "c2c.auth.github.client_id"
GITHUB_CLIENT_ID_ENV = "C2C_AUTH_GITHUB_CLIENT_ID"
GITHUB_CLIENT_SECRET_PROP = "c2c.auth.github.client_secret"  # nosec # noqa
GITHUB_CLIENT_SECRET_ENV = "C2C_AUTH_GITHUB_CLIENT_SECRET"  # nosec # noqa
GITHUB_SCOPE_PROP = "c2c.auth.github.scope"
GITHUB_SCOPE_ENV = "C2C_AUTH_GITHUB_SCOPE"
GITHUB_AUTH_COOKIE_PROP = "c2c.auth.github.auth.cookie"
GITHUB_AUTH_COOKIE_ENV = "C2C_AUTH_GITHUB_COOKIE"
GITHUB_AUTH_SECRET_PROP = "c2c.auth.github.auth.secret"  # nosec # noqa
GITHUB_AUTH_SECRET_ENV = "C2C_AUTH_GITHUB_SECRET"  # nosec # noqa


LOG = logging.getLogger(__name__)


def get_expected_secret(request: pyramid.request.Request) -> str:
    """Return the secret expected from the client."""
    settings = request.registry.settings
    return cast(str, env_or_settings(settings, SECRET_ENV, SECRET_PROP, False))


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


class UserDetails(TypedDict, total=False):
    """Details about the user authenticated with GitHub."""

    login: str
    name: str
    url: str
    token: str


def _is_auth_secret(request: pyramid.request.Request) -> bool:
    expected = get_expected_secret(request)
    secret = request.params.get("secret")
    if secret is None:
        secret = request.headers.get("X-API-Key")
    if secret is None:
        secret_hash = request.cookies.get(SECRET_ENV)
    else:
        secret_hash = _hash_secret(secret)

    if secret_hash is not None:
        if secret_hash == "" or secret == "":  # nosec
            # logout
            request.response.delete_cookie(SECRET_ENV)
            return False
        if secret_hash != _hash_secret(expected):
            return False
        # login or refresh the cookie
        request.response.set_cookie(SECRET_ENV, secret_hash, max_age=COOKIE_AGE, httponly=True)
        # since this could be used from outside c2cwsgiutils views, we cannot set the path to c2c
        return True
    return False


def _is_auth_user_github(request: pyramid.request.Request) -> Tuple[bool, UserDetails]:

    settings = request.registry.settings
    cookie = request.cookies.get(
        env_or_settings(
            settings,
            GITHUB_AUTH_COOKIE_ENV,
            GITHUB_AUTH_COOKIE_PROP,
            "c2c-auth-jwt",
        ),
        "",
    )
    try:
        return True, cast(
            UserDetails,
            jwt.decode(
                cookie,
                env_or_settings(
                    settings,
                    GITHUB_AUTH_SECRET_ENV,
                    GITHUB_AUTH_SECRET_PROP,
                ),
                algorithms=["HS256"],
            ),
        )
    except jwt.exceptions.InvalidTokenError as e:
        LOG.warning("Error no decoding JWT token: %s", e)
    return False, {}


def is_auth_user(request: pyramid.request.Request) -> Tuple[bool, UserDetails]:
    """
    Check if the client is authenticated.

    Returns: boolean to indicated if the user is authenticated, and a dictionary with user details.
    """
    settings = request.registry.settings
    auth_type_ = auth_type(settings)
    if auth_type_ == AuthenticationType.NONE:
        return False, {}
    if auth_type_ == AuthenticationType.SECRET:
        return _is_auth_secret(request), {}
    if auth_type_ == AuthenticationType.GITHUB:
        return _is_auth_user_github(request)

    return False, {}


def is_auth(request: pyramid.request.Request) -> bool:
    """Check if the client is authenticated."""
    auth, _ = is_auth_user(request)
    return auth


def auth_view(request: pyramid.request.Request) -> None:
    """Get the authentication view."""
    if not is_auth(request):
        raise HTTPForbidden("Missing or invalid secret (parameter, X-API-Key header or cookie)")


class AuthenticationType(Enum):
    """The type of authentication."""

    # No Authentication configured
    NONE = 0
    # Authentication with a shared secret
    SECRET = 1
    # Authentication on GitHub and by having an access on a repository
    GITHUB = 2


def auth_type(settings: Optional[Mapping[str, Any]]) -> Optional[AuthenticationType]:
    """Get the authentication type."""
    if env_or_settings(settings, SECRET_ENV, SECRET_PROP, "") != "":
        return AuthenticationType.SECRET

    has_client_id = env_or_settings(settings, GITHUB_CLIENT_ID_ENV, GITHUB_CLIENT_ID_PROP, "") != ""
    has_client_secret = (
        env_or_settings(settings, GITHUB_CLIENT_SECRET_ENV, GITHUB_CLIENT_SECRET_PROP, "") != ""
    )
    has_repo = env_or_settings(settings, GITHUB_REPOSITORY_ENV, GITHUB_REPOSITORY_PROP, "") != ""
    secret = env_or_settings(settings, GITHUB_AUTH_SECRET_ENV, GITHUB_AUTH_SECRET_PROP, "")
    has_secret = len(secret) >= 16
    if secret and not has_secret:
        LOG.error(
            "You set a too short secret (length: %i) to protect the admin page, it should have "
            "at lease a length of 16",
            len(secret),
        )

    if has_client_id and has_client_secret and has_repo and has_secret:
        return AuthenticationType.GITHUB

    return AuthenticationType.NONE


def is_enabled(
    config: pyramid.config.Configurator, env_name: Optional[str] = None, config_name: Optional[str] = None
) -> bool:
    """Is the authentication enable."""
    return (
        config_bool(env_or_config(config, env_name, config_name))
        and auth_type(config.get_settings()) is not None
    )
