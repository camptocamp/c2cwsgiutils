Camptocamp WSGI utilities
=========================

This is a python library providing common tools for Camptocamp WSGI
applications:

* Provide a small framework for gathering performance statistics about
  a web application (statsd protocol)
* Allow to use a master/slave PostgresQL configuration
* Logging handler for CEE/UDP logs
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
