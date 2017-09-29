from pyramid.renderers import JSON


class PrettyJSON(JSON):
    def __call__(self, info):
        # Cannot just wrap JSON with a special indent version. Cornice is monkeypatching the hell out of
        # the JSON renderer. See cornice.util._JsonRenderer
        def _render(value, system):
            request = system.get('request')
            default = self._make_default(request)
            if request is not None:
                response = request.response
                ct = response.content_type
                if ct == response.default_content_type:
                    response.content_type = 'application/json'
                if 'c2c_pretty' in request.params:
                    return self.serializer(value, default=default, indent=4, **self.kw)
            return self.serializer(value, default=default, **self.kw)

        return _render


def init(config):
    config.add_renderer('json', PrettyJSON())
