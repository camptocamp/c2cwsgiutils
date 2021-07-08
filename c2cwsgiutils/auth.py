import hashlib
from typing import Optional, cast

import pyramid.request
from pyramid.httpexceptions import HTTPForbidden

# noinspection PyProtectedMember
from c2cwsgiutils.config_utils import config_bool, env_or_config, env_or_settings

COOKIE_AGE = 7 * 24 * 3600
SECRET_PROP = "c2c.secret"  # nosec  # noqa
SECRET_ENV = "C2C_SECRET"  # nosec  # noqa


def get_expected_secret(request: pyramid.request.Request) -> str:
    """
    Returns the secret expected from the client.
    """
    settings = request.registry.settings
    return cast(str, env_or_settings(settings, SECRET_ENV, SECRET_PROP, False))


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def is_auth(request: pyramid.request.Request) -> bool:
    """
    Check if the client is authenticated with the C2C_SECRET.
    """
    expected = get_expected_secret(request)
    secret = request.params.get("secret")
    if secret is None:
        secret = request.headers.get("X-API-Key")

    if secret is not None:
        if secret == "":  # nosec
            # logout
            request.response.delete_cookie(SECRET_ENV)
            return False
        if secret != expected:
            return False
        # login or refresh the cookie
        request.response.set_cookie(SECRET_ENV, _hash_secret(secret), max_age=COOKIE_AGE, httponly=True)
        # since this could be used from outside c2cwsgiutils views, we cannot set the path to c2c
        return True

    # secret not found in the params or the headers => try with the cookie

    secret = request.cookies.get(SECRET_ENV)
    if secret is not None:
        if secret != _hash_secret(expected):
            return False
        request.response.set_cookie(SECRET_ENV, secret, max_age=COOKIE_AGE, httponly=True)
        return True
    return False


def auth_view(request: pyramid.request.Request) -> None:
    if not is_auth(request):
        raise HTTPForbidden("Missing or invalid secret (parameter, X-API-Key header or cookie)")


def is_enabled(
    config: pyramid.config.Configurator, env_name: Optional[str] = None, config_name: Optional[str] = None
) -> bool:
    return (
        config_bool(env_or_config(config, env_name, config_name))
        and env_or_config(config, SECRET_ENV, SECRET_PROP, "") != ""
    )
