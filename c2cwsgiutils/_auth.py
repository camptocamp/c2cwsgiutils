from pyramid.httpexceptions import HTTPForbidden
import pyramid.request

from c2cwsgiutils._utils import env_or_settings


def auth_view(request: pyramid.request.Request, env_name: str, config_name: str) -> None:
    secret = request.params.get('secret')
    if secret is None:
        secret = request.headers.get('X-API-Key')
    if secret != env_or_settings(request.registry.settings, env_name, config_name, False):
        raise HTTPForbidden('Missing or invalid secret (parameter or X-API-Key header)')
