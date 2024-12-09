import logging
from typing import Optional, cast

from plaster_pastedeploy import Loader as BaseLoader

from c2cwsgiutils import get_config_defaults, get_logconfig_dict

_LOG = logging.getLogger(__name__)


class Loader(BaseLoader):  # type: ignore
    """The application loader."""

    def _get_defaults(self, defaults: Optional[dict[str, str]] = None) -> dict[str, str]:
        d = get_config_defaults()
        d.update(defaults or {})
        return cast(dict[str, str], super()._get_defaults(d))

    def __repr__(self) -> str:
        """Get the object representation."""
        return f'c2cwsgiutils.loader.Loader(uri="{self.uri}")'

    def setup_logging(self, defaults: Optional[dict[str, str]] = None) -> None:
        """
        Set up logging via :func:`logging.config.dictConfig` with value returned from c2cwsgiutils.get_logconfig_dict.

        Defaults are specified for the special ``__file__`` and ``here``
        variables, similar to PasteDeploy config loading. Extra defaults can
        optionally be specified as a dict in ``defaults``.

        Arguments:
        ---------
        defaults: The defaults that will be used when passed to
            :func:`logging.config.fileConfig`.

        """
        if "loggers" in self.get_sections():
            logging.config.dictConfig(get_logconfig_dict(self.uri.path))
        else:
            logging.basicConfig()
