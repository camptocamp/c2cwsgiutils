from pyramid.renderers import JSON


def init(config):
    config.add_renderer('json', JSON(indent=4))
