import functools
import json
import logging
from typing import Any

import requests

from c2cwsgiutils.acceptance import connection, utils

_LOG = logging.getLogger(__name__)


class PrintConnection(connection.Connection):
    """A Connection with specialized methods to interact with a Mapfish Print server."""

    def __init__(self, base_url: str, origin: str) -> None:
        """
        Initialize.

        Arguments:
            base_url: The base URL to the print server (including the /print)
            app: The name of the application to use
            origin: The origin and referrer to include in the requests

        """
        super().__init__(base_url=base_url, origin=origin)
        self.session.headers["Referrer"] = origin

    def wait_ready(self, timeout: int = 60, app: str = "default") -> None:
        """Wait the print instance to be ready."""
        utils.retry_timeout(functools.partial(self.get_capabilities, app=app), timeout=timeout)

    def get_capabilities(self, app: str) -> Any:
        """Get the capabilities for the given application."""
        return self.get_json(app + "/capabilities.json", cache_expected=connection.CacheExpected.YES)

    def get_example_requests(self, app: str) -> dict[str, Any]:
        """Get the example requests for the given application."""
        samples = self.get_json(app + "/exampleRequest.json", cache_expected=connection.CacheExpected.YES)
        out = {}
        for name, value in samples.items():
            out[name] = json.loads(value)
        return out

    def get_pdf(self, app: str, request: dict[str, Any], timeout: int = 60) -> requests.Response:
        """Create a report and wait for it to be ready."""
        create_report = self.post_json(app + "/report.pdf", json=request)
        _LOG.debug("create_report=%s", create_report)
        ref = create_report["ref"]

        status = utils.retry_timeout(functools.partial(self._check_completion, ref), timeout=timeout)
        _LOG.debug("status=%s", repr(status))
        assert status["status"] == "finished"

        report = self.get_raw("report/" + ref)
        assert report.headers["Content-Type"] == "application/pdf"
        return report

    def _check_completion(self, ref: str) -> Any | None:
        status = self.get_json(f"status/{ref}.json")
        if status["done"]:
            return status
        return None

    def get_apps(self) -> Any:
        """Get the list of available applications."""
        return self.get_json("apps.json", cache_expected=connection.CacheExpected.YES)
