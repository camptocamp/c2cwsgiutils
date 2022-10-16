FROM ubuntu:22.04 AS base-all-0
LABEL maintainer Camptocamp "info@camptocamp.com"
SHELL ["/bin/bash", "-o", "pipefail", "-cux"]

RUN --mount=type=cache,target=/var/lib/apt/lists \
  --mount=type=cache,target=/var/cache,sharing=locked \
  apt-get update \
  && apt-get upgrade --assume-yes \
  && apt-get install --assume-yes --no-install-recommends python3-pip

# Used to convert the locked packages by poetry to pip requirements format
# We don't directly use `poetry install` because it force to use a virtual environment.
FROM base-all-0 as poetry

# Install Poetry
WORKDIR /tmp
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install --disable-pip-version-check --requirement=requirements.txt

# Do the conversion
COPY poetry.lock pyproject.toml ./
RUN poetry export --extras=all --output=requirements.txt \
  && poetry export --extras=all --with=dev --output=requirements-dev.txt

# Base, the biggest thing is to install the Python packages
FROM base-all-0 as base-all

# The /poetry/requirements.txt file is build with the command
# poetry export --extras=all --output=requirements.txt, see above
# hadolint ignore=SC2086
RUN --mount=type=cache,target=/var/lib/apt/lists \
  --mount=type=cache,target=/var/cache,sharing=locked \
  --mount=type=cache,target=/root/.cache \
  --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
  apt-get update \
  && DEV_PACKAGES="libpq-dev build-essential python3-dev" \
  && apt-get install --yes --no-install-recommends \
    libpq5 curl postgresql-client net-tools iputils-ping gnupg apt-transport-https \
    $DEV_PACKAGES \
  && python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements.txt \
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
# The /poetry/requirements.txt file is build with the command
# poetry export --extras=all --dev --output=requirements-dev.txt, see above
RUN --mount=type=cache,target=/root/.cache \
  --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
  python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements-dev.txt

FROM base-all AS base

WORKDIR /opt/c2cwsgiutils
COPY c2cwsgiutils ./c2cwsgiutils
COPY pyproject.toml README.md ./
# The sed is to deactivate the poetry-dynamic-versioning plugin.
ENV POETRY_DYNAMIC_VERSIONING_BYPASS=dev
RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install --disable-pip-version-check --no-deps --editable=. \
  && python3 -m compileall -q \
  && python3 -m compileall /usr/local/lib/python3.* /usr/lib/python3.* . -q \
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

WORKDIR /opt/c2cwsgiutils
COPY c2cwsgiutils ./c2cwsgiutils
COPY pyproject.toml README.md ./
# The sed is to deactivate the poetry-dynamic-versioning plugin.
ENV POETRY_DYNAMIC_VERSIONING_BYPASS=dev
RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install --disable-pip-version-check --no-deps --editable=. \
  && python3 -m pip freeze > /requirements.txt

WORKDIR /opt/c2cwsgiutils

FROM base as standard
