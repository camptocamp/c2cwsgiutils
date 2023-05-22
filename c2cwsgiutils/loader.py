import logging
from typing import Dict, Optional, cast

from plaster_pastedeploy import Loader as BaseLoader

from c2cwsgiutils import get_config_defaults

LOG = logging.getLogger(__name__)


class Loader(BaseLoader):  # type: ignore
    """The application loader."""

    def _get_defaults(self, defaults: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        d = get_config_defaults()
        d.update(defaults or {})
        return cast(Dict[str, str], super()._get_defaults(d))

    def __repr__(self) -> str:
        """Get the object representation."""
        return f'c2cwsgiutils.loader.Loader(uri="{self.uri}")'
