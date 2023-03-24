# Release 4

BREAKING CHANGES:

- Rename the scripts:

  - c2cwsgiutils_run => c2cwsgiutils-run
  - c2cwsgiutils_genversion.py => c2cwsgiutils-genversion
  - c2cwsgiutils_coverage_report.py => c2cwsgiutils-coverage-report
  - c2cwsgiutils_stats_db.py => c2cwsgiutils-stats-db
  - c2cwsgiutils_test_print.py => c2cwsgiutils-test-print
  - c2cwsgiutils_check_es.py => c2cwsgiutils-check-es

- `C2C_DISABLE_EXCEPTION_HANDLING` is replaced by `C2C_ENABLE_EXCEPTION_HANDLING` and is disabled by default.

- /!\ initialization must be explicit:
  import c2cwsgiutils.setup_process
  c2cwsgiutils.setup_process.init()

- The base image is now ubuntu 20.04
