Camptocamp WSGI utilities
=========================

This is a python library providing common tools for Camptocamp WSGI
applications:

* Provide a small framework for gathering performance statistics about
  a web application (statsd protocol)
* Allow to use a master/slave PostgresQL configuration
* Logging handler for CEE/UDP logs
  * An optional (enabled by setting the LOG_VIEW_SECRET env var) view (/logging/level)
    to change runtime the log levels
* SQL profiler to debug DB performance problems, disabled by default. You must enable it by setting the
  SQL_PROFILER_SECRET env var and using the view (/sql_profiler) to switch it ON and OFF. Warning,
  it will slow down everything.
* A view to get the version information about the application and the installed packages (/versions.json)
* A framework for implementing a health_check service (/health_check)
* Error handlers to send JSON messages to the client in case of error
* A cornice service drop in replacement for setting up CORS

Also provide tools for writing acceptance tests:

* A class that can be used from a py.test fixture to control a
  composition
* A class that can be used from a py.text fixture to test a REST API

As an example on how to use it in an application, you can look at the
test application in [acceptance_tests/app](acceptance_tests/app).
To see how to test such an application, look at
[acceptance_tests/tests](acceptance_tests/tests).


Developer info
--------------

You will need `docker` (>=1.12.0), `docker-compose` (>=1.10.0), twine and
`make` installed on the machine to play with this project.
Check available versions of `docker-engine` with
`apt-get policy docker-engine` and eventually force install the
up-to-date version using a command similar to
`apt-get install docker-engine=1.12.3-0~xenial`.

To lint and test everything, run the following command:

```shell
make
```

Make sure you are strict with the version numbers:

* bug fix version change: Nothing added, removed or changed in the API and only bug fix
  version number changes in the dependencies
* minor version change: The API must remain backward compatible and only minor version
  number changes in the dependencies
* major version change: The API and the dependencies are not backward compatible

To make a release:

* Change the the version in [setup.py](setup.py)
* run `make release`
