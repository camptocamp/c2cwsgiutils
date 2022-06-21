FROM camptocamp/c2cwsgiutils as base-all
LABEL maintainer Camptocamp "info@camptocamp.com"
SHELL ["/bin/bash", "-o", "pipefail", "-cux"]

# Used to convert the locked packages by poetry to pip requirements format
# We don't directly use `poetry install` because it force to use a virtual environment.
FROM base-all as poetry

# Install Poetry
WORKDIR /tmp
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install --disable-pip-version-check --requirement=requirements.txt

# Do the conversion
COPY poetry.lock pyproject.toml ./
RUN poetry export --output=requirements.txt \
  && poetry export --dev --output=requirements-dev.txt

# Base, the biggest thing is to install the Python packages
FROM base-all as base

WORKDIR /app

EXPOSE 8080
RUN --mount=type=cache,target=/root/.cache \
  --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
  python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements.txt

COPY . /app

ARG GIT_HASH

RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install --disable-pip-version-check --no-deps --editable=.
RUN ./models_graph.py > models.dot \
  && ./models_graph.py Hello > models-hello.dot \
  && c2cwsgiutils-genversion $GIT_HASH \
  && python3 -m compileall -q .

ENV \
  DOCKER_RUN=1 \
  DEVELOPMENT=0 \
  SQLALCHEMY_POOL_RECYCLE=30 \
  SQLALCHEMY_POOL_SIZE=5 \
  SQLALCHEMY_MAX_OVERFLOW=25 \
  SQLALCHEMY_SLAVE_POOL_RECYCLE=30 \
  SQLALCHEMY_SLAVE_POOL_SIZE=5 \
  SQLALCHEMY_SLAVE_MAX_OVERFLOW=25 LOG_TYPE=console \
  OTHER_LOG_LEVEL=WARNING \
  GUNICORN_LOG_LEVEL=WARNING \
  GUNICORN_ACCESS_LOG_LEVEL=INFO \
  SQL_LOG_LEVEL=WARNING \
  C2CWSGIUTILS_LOG_LEVEL=WARNING \
  LOG_LEVEL=INFO

# www-data
USER 33
