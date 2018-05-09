from pyramid.httpexceptions import HTTPForbidden
import pyramid.request

# noinspection PyProtectedMember
from c2cwsgiutils._utils import env_or_settings


def is_auth(request: pyramid.request.Request, env_name: str, config_name: str) -> bool:
    secret = request.params.get('secret')
    if secret is None:
        secret = request.headers.get('X-API-Key')
    return secret == env_or_settings(request.registry.settings, env_name, config_name, False)


def auth_view(request: pyramid.request.Request, env_name: str, config_name: str) -> None:
    if not is_auth(request, env_name, config_name):
        raise HTTPForbidden('Missing or invalid secret (parameter or X-API-Key header)')
