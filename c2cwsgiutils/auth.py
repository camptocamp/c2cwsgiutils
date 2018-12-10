from pyramid.httpexceptions import HTTPForbidden
import pyramid.request
from typing import Optional

# noinspection PyProtectedMember
from c2cwsgiutils._utils import env_or_settings, env_or_config, config_bool

SECRET_PROP = 'c2c.secret'
SECRET_ENV = 'C2C_SECRET'


def _get_secret(settings: dict, env_name: Optional[str]=None, config_name: Optional[str]=None) -> str:
    secret = env_or_settings(settings, env_name, config_name) if \
        env_name is not None or config_name is not None else None
    if secret is None:
        secret = env_or_settings(settings, SECRET_ENV, SECRET_PROP, False)
    return secret


def is_auth(
        request: pyramid.request.Request,
        env_name: Optional[str]=None, config_name: Optional[str]=None) -> bool:
    secret = request.params.get('secret')
    if secret is None:
        secret = request.headers.get('X-API-Key')
    return secret == _get_secret(request.registry.settings, env_name, config_name)


def auth_view(
        request: pyramid.request.Request,
        env_name: Optional[str]=None, config_name: Optional[str]=None) -> None:
    if not is_auth(request, env_name, config_name):
        raise HTTPForbidden('Missing or invalid secret (parameter or X-API-Key header)')


def is_enabled(
        config: pyramid.config.Configurator,
        env_name: Optional[str]=None, config_name: Optional[str]=None) -> bool:
    return config_bool(env_or_config(config, env_name, config_name)) and \
        env_or_config(config, SECRET_ENV, SECRET_PROP, '') != ''
