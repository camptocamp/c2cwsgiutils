import pyramid.config
from pyramid.renderers import JSON


def init(config: pyramid.config.Configurator) -> None:
    config.add_renderer('json', JSON(indent=4))
