import os
from plaster_pastedeploy import Loader as BaseLoader
from typing import Dict


class Loader(BaseLoader):

    def _get_defaults(self, defaults: dict = None) -> dict:
        d: Dict[str, str] = {}
        d.update(os.environ)
        d.update(defaults or {})
        settings = super()._get_defaults(d)
        return settings

    def __repr__(self) -> str:
        return 'c2cwsgiutils.loader.Loader(uri="{0}")'.format(self.uri)
