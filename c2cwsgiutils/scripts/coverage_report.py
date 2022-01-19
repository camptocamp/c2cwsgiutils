#!/usr/bin/env python3
import logging
import os
import shutil
import sys
import warnings

import coverage

LOG = logging.getLogger(__name__)


def deprecated() -> None:
    """Run the command and print a deprecated notice."""
    warnings.warn("c2cwsgiutils_coverage_report.py is deprecated; use c2cwsgiutils-coverage-report instead")
    return main()


def main() -> None:
    """Run the command."""
    sources = sys.argv[1:]
    report_dir = "/reports/coverage/api"
    dest_dir = "/tmp/coverage/api"  # nosec
    shutil.rmtree(dest_dir, ignore_errors=True)
    shutil.copytree(report_dir, dest_dir)
    cov = coverage.Coverage(
        data_file=os.path.join(dest_dir, "coverage"), data_suffix=True, source=sources or None, branch=True
    )
    cov.combine([dest_dir], strict=True)
    cov.html_report(directory=dest_dir, ignore_errors=True)
    cov.xml_report(outfile=os.path.join(dest_dir, "coverage.xml"), ignore_errors=True)
    cov.report(ignore_errors=True)


if __name__ == "__main__":
    main()
