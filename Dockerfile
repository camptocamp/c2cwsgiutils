FROM ubuntu:22.04 AS base-all
LABEL maintainer "info@camptocamp.org"

COPY requirements.txt Pipfile* /opt/c2cwsgiutils/
# hadolint ignore=SC2086
RUN apt-get update \
  && DEV_PACKAGES="libpq-dev build-essential python3-dev" \
  && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
    libpq5 \
    python3 \
    curl \
    postgresql-client \
    net-tools iputils-ping screen \
    gnupg \
    apt-transport-https \
    $DEV_PACKAGES \
  && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
    python3-pip \
    python3-pkgconfig \
  && apt-get clean \
  && rm -r /var/lib/apt/lists/* \
  && python3 -m pip install --no-cache-dir --requirement=/opt/c2cwsgiutils/requirements.txt \
  && cd /opt/c2cwsgiutils/ && pipenv sync --system --clear && cd - \
  && strip /usr/local/lib/python3.*/dist-packages/*/*.so \
  && apt-get remove --purge --autoremove --yes $DEV_PACKAGES binutils

ENV TERM=linux \
  LANG=C.UTF-8 \
  LOG_TYPE=console \
  LOG_HOST=localhost \
  LOG_PORT=514 \
  SQL_LOG_LEVEL=WARN \
  GUNICORN_LOG_LEVEL=WARN \
  OTHER_LOG_LEVEL=WARN \
  DEVELOPMENT=0 \
  PKG_CONFIG_ALLOW_SYSTEM_LIBS=OHYESPLEASE

FROM base-all AS base-lint
RUN cd /opt/c2cwsgiutils/ && pipenv sync --system --clear --dev && cd -

FROM base-all AS base

COPY scripts/c2cwsgiutils-run /opt/c2cwsgiutils/scripts/
COPY setup.py setup.cfg /opt/c2cwsgiutils/
COPY c2cwsgiutils /opt/c2cwsgiutils/c2cwsgiutils
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir --no-deps \
  --editable=/opt/c2cwsgiutils \
  && python3 -m compileall -q \
  && python3 -m compileall /usr/local/lib/python3.* /usr/lib/python3.* /opt/c2cwsgiutils -q \
    -x '/usr/local/lib/python3.*/dist-packages/pipenv/' \
  && python3 -c 'import c2cwsgiutils'

ENV C2C_BASE_PATH=/c2c \
  C2C_REDIS_URL= \
  C2C_REDIS_SENTINELS= \
  C2C_REDIS_SERVICENAME=mymaster \
  C2C_REDIS_DB=0 \
  C2C_REDIS_OPTIONS=socket_timeout=3 \
  C2C_BROADCAST_PREFIX=broadcast_api_ \
  C2C_REQUEST_ID_HEADER= \
  C2C_REQUESTS_DEFAULT_TIMEOUT= \
  C2C_SQL_PROFILER_ENABLED=0 \
  C2C_PROFILER_PATH= \
  C2C_PROFILER_MODULES= \
  C2C_DEBUG_VIEW_ENABLED=0 \
  C2C_LOG_VIEW_ENABLED=0 \
  C2C_DB_MAINTENANCE_VIEW_ENABLED=0 \
  C2C_ENABLE_EXCEPTION_HANDLING=0 \
  SENTRY_URL= \
  SENTRY_CLIENT_ENVIRONMENT=dev \
  SENTRY_CLIENT_RELEASE=latest \
  SENTRY_TAG_SERVICE=app

CMD ["/usr/local/bin/gunicorn"]

FROM base-lint as tests

COPY . /opt/c2cwsgiutils/
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir --no-deps \
  --editable=/opt/c2cwsgiutils
RUN cd /opt/c2cwsgiutils/ && prospector -X --output=pylint
RUN cd /opt/c2cwsgiutils/ && pytest -vv --cov=c2cwsgiutils --color=yes tests && rm -r tests

FROM base as standard
