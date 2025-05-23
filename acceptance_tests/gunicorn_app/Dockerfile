FROM camptocamp/c2cwsgiutils AS base-all
LABEL org.opencontainers.image.authors="Camptocamp <info@camptocamp.com>"
SHELL ["/bin/bash", "-o", "pipefail", "-cux"]

# Used to convert the locked packages by poetry to pip requirements format
# We don't directly use `poetry install` because it force to use a virtual environment.
FROM base-all AS poetry

RUN --mount=type=cache,target=/var/lib/apt/lists \
  --mount=type=cache,target=/var/cache,sharing=locked \
  apt-get update \
  && apt-get install --assume-yes --no-install-recommends python-is-python3

# Install Poetry
WORKDIR /tmp
COPY requirements.txt ./
RUN python3 -m pip install --disable-pip-version-check --requirement=requirements.txt

# Do the conversion
COPY poetry.lock pyproject.toml ./
RUN poetry export --output=requirements.txt \
  && poetry export --with=dev --output=requirements-dev.txt

# Base, the biggest thing is to install the Python packages
FROM base-all AS base

WORKDIR /app

EXPOSE 8080
RUN --mount=type=cache,target=/root/.cache \
  --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
  python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements.txt

COPY . /app

ARG GIT_HASH

RUN --mount=type=cache,target=/root/.cache \
  python3 -m pip install --disable-pip-version-check --no-deps --editable=. \
  && python3 -m pip freeze > /requirements.txt
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
  SQLALCHEMY_SLAVE_MAX_OVERFLOW=25 \
  LOG_TYPE=console \
  OTHER_LOG_LEVEL=WARNING \
  GUNICORN_LOG_LEVEL=WARNING \
  SQL_LOG_LEVEL=WARNING \
  C2CWSGIUTILS_LOG_LEVEL=WARNING \
  LOG_LEVEL=INFO \
  VISIBLE_ENTRY_POINT=/

RUN mkdir -p /prometheus-metrics \
  && chmod a+rwx /prometheus-metrics
ENV PROMETHEUS_MULTIPROC_DIR=/prometheus-metrics

# www-data
USER 33

CMD ["/venv/bin/gunicorn", "--paste=/app/production.ini"]
