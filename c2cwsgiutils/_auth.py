from pyramid.httpexceptions import HTTPForbidden

from c2cwsgiutils._utils import env_or_settings


def auth_view(request, env_name, config_name):
    if request.params.get('secret') != env_or_settings(request.registry.settings, env_name, config_name,
                                                       False):
        raise HTTPForbidden('Missing or invalid secret parameter')
