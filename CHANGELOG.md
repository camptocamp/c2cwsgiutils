# Release 5.1

- `setup_process.init` initialize all non-wsgi features in a similar way as the `pyramid.includeme` function.
- Restore the `C2CWSGIUTILS_CONFIG` environment variable, you can still use the standard way to specify the
  config file (with the argument `--paste` of Gunicorn, or the `config_uri` argument or `pserve` prefixed
  by `c2c://`).
- Move back the logging configuration to `production.ini`. It will be read from `gunicorn.conf.py` at startup.
- Remove the `development.ini` file to simplify the default application template; restore `production.ini` has the default configuration file.
- When the `auth_type` is GitHub the `is_auth` and the `has_access` can return different values, the `is_auth` will just check
  the authentication on GitHub succeed, `has_access` also check that the user has the desired rights.
- The base image is now Ubuntu 22.04.
- The `install-docker` and `install-gdal` are removed.
- It is recommended to use OAuth2 with GitHub login instead of the `C2C_SECRET` because it protects from
  brute force attacks and the access grant is personal and can be revoked.

# Release 5.0

- Remove the script `c2cwsgiutils-run`.
- The Pyramid initializing module functions are renamed from `init` to `includeme`.
- Remove the environment variable `GUNICORN_PARAMS` we will use the standard one `GUNICORN_CMD_ARGS`.
- Remove the `C2CWSGIUTILS_CONFIG` environment variable, we should use the standard way to specify the
  config file (with the argument `--paste` of Gunicorn, or the `config_uri` argument or `pserve` prefixed
  by `c2c://`).
- Filters like `sentry`, `profiler`, `client_info` will not be added automatically anymore, you should add
  the following lines in your project `development.ini`:

  ```ini
  [pipeline:main]
  pipeline = egg:c2cwsgiutils#client_info egg:c2cwsgiutils#profiler egg:c2cwsgiutils#sentry app
  ```

  and in your `production.ini`:

  ```ini
  [pipeline:main]
  pipeline = egg:c2cwsgiutils#client_info egg:c2cwsgiutils#sentry app
  ```

  and in both `development.ini` and `production.ini`, rename `[app:main]` to `[app:app]`.

- The usage of the Docker image is deprecated, read the start of the [Readme](./README.md) to update your setup.
- The usage of the global `DBSession` is deprecated, use the session on the request instead, should be
  initialized with the function `c2cwsgiutils.db.init`. see the [Readme](./README.md) for more information.

# Release 4

- Rename the scripts:

  - c2cwsgiutils_run => c2cwsgiutils-run
  - c2cwsgiutils_genversion.py => c2cwsgiutils-genversion
  - c2cwsgiutils_coverage_report.py => c2cwsgiutils-coverage-report
  - c2cwsgiutils_stats_db.py => c2cwsgiutils-stats-db
  - c2cwsgiutils_test_print.py => c2cwsgiutils-test-print
  - c2cwsgiutils_check_es.py => c2cwsgiutils-check-es

- `C2C_DISABLE_EXCEPTION_HANDLING` is replaced by `C2C_ENABLE_EXCEPTION_HANDLING` and is disabled by default.
