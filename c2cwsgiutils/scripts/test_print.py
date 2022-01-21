#!/usr/bin/env python3
"""Test a MapfishPrint server."""
import argparse
import logging
import pprint
import warnings

import c2cwsgiutils.setup_process
from c2cwsgiutils.acceptance.print import PrintConnection

LOG = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    c2cwsgiutils.setup_process.fill_arguments(parser)
    parser.add_argument("--url", required=True, help="The base URL of the print, including the '/print'")
    parser.add_argument("--app", default=None, help="The print application name")
    parser.add_argument("--referrer", default=None, help="The referrer (defaults to --url)")
    parser.add_argument("--verbose", default=False, action="store_true", help="Enable debug output")
    return parser.parse_args()


def deprecated() -> None:
    """Run the command and print a deprecated notice."""
    warnings.warn("c2cwsgiutils_test_print.py is deprecated; use c2cwsgiutils-test-print instead")
    return main()


def main() -> None:
    """Run the command."""
    args = _parse_args()
    c2cwsgiutils.setup_process.bootstrap_application_from_options(args)
    if not args.verbose:
        logging.root.setLevel(logging.INFO)
    print_ = PrintConnection(base_url=args.url, origin=args.referer if args.referer else args.url)
    print_.wait_ready(app=args.app)
    if args.app is None:
        for app in print_.get_apps():
            if app != "default":
                LOG.info("\n\n%s=================", app)
                test_app(print_, app)
    else:
        test_app(print_, args.app)


def test_app(print_: PrintConnection, app: str) -> None:
    """Test the application."""
    capabilities = print_.get_capabilities(app)
    LOG.debug("Capabilities:\n%s", pprint.pformat(capabilities))
    examples = print_.get_example_requests(app)
    for name, request in examples.items():
        LOG.info("\n%s-----------------", name)
        pdf = print_.get_pdf(app, request)
        size = len(pdf.content)
        LOG.info("Size=%d", size)


if __name__ == "__main__":
    main()
