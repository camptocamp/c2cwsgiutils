#!/usr/bin/env python3
import coverage
import os
import shutil
import sys


def main():
    sources = sys.argv[1:]
    report_dir = '/reports/coverage/api'
    dest_dir = '/tmp/coverage/api'
    shutil.rmtree(dest_dir, ignore_errors=True)
    shutil.copytree(report_dir, dest_dir)
    cov = coverage.Coverage(data_file='coverage', data_suffix=True, source=sources, branch=True)
    cov.combine([dest_dir], strict=True)
    cov.html_report(directory=dest_dir, ignore_errors=True)
    cov.xml_report(outfile=os.path.join(dest_dir, 'coverage.xml'), ignore_errors=True)
    cov.report(ignore_errors=True)

main()
