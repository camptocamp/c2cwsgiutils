#!/usr/bin/env python3
"""
Test a MapfishPrint server.
"""
import c2cwsgiutils.setup_process  # noqa  # pylint: disable=unused-import

import argparse
import logging
import pprint

from c2cwsgiutils.acceptance.print import PrintConnection

LOG = logging.getLogger("c2cwsgiutils_test_print")


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="The base URL of the print, including the '/print'")
    parser.add_argument("--app", default=None, help="The app name")
    parser.add_argument("--referer", default=None, help="The referer (defaults to --url)")
    parser.add_argument("--verbose", default=False, action="store_true", help="Enable debug output")
    return parser.parse_args()


def main():
    args = _parse_args()
    if not args.verbose:
        logging.root.setLevel(logging.INFO)
    p = PrintConnection(base_url=args.url, origin=args.referer if args.referer else args.url)
    p.wait_ready(app=args.app)
    if args.app is None:
        for app in p.get_apps():
            if app != 'default':
                print("\n\n" + app + "=================")
                test_app(p, app)
    else:
        test_app(p, args.app)


def test_app(p, app):
    capabilities = p.get_capabilities(app)
    LOG.debug("Capabilities:\n%s", pprint.pformat(capabilities))
    examples = p.get_example_requests(app)
    for name, request in examples.items():
        print("\n" + name + "-----------------")
        pdf = p.get_pdf(app, request)
        size = len(pdf.content)
        print("Size=" + str(size))


main()
