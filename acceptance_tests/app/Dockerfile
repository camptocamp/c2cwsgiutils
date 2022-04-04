FROM camptocamp/c2cwsgiutils
LABEL maintainer "info@camptocamp.org"

WORKDIR /app

EXPOSE 8080

COPY Pipfile Pipfile.lock /tmp/
# hadolint ignore=DL3003
RUN \
    cd /tmp && \
    pipenv sync --system --clear --dev && \
    rm --recursive --force /tmp/* /root/.cache/*

COPY . /app

ARG GIT_HASH

RUN python3 -m pip install --no-cache-dir --editable=.
# hadolint ignore=DL3059
RUN ./models_graph.py > models.dot && \
    ./models_graph.py Hello > models-hello.dot && \
    c2cwsgiutils-genversion $GIT_HASH && \
    prospector && \
    python3 -m compileall -q .

ENV \
    DOCKER_RUN=1 \
    DEVELOPMENT=0 \
    SQLALCHEMY_POOL_RECYCLE=30 \
    SQLALCHEMY_POOL_SIZE=5 \
    SQLALCHEMY_MAX_OVERFLOW=25 \
    SQLALCHEMY_SLAVE_POOL_RECYCLE=30 \
    SQLALCHEMY_SLAVE_POOL_SIZE=5 \
    SQLALCHEMY_SLAVE_MAX_OVERFLOW=25\
    LOG_TYPE=console \
    OTHER_LOG_LEVEL=WARNING \
    GUNICORN_LOG_LEVEL=WARNING \
    GUNICORN_ACCESS_LOG_LEVEL=INFO \
    SQL_LOG_LEVEL=WARNING \
    C2CWSGIUTILS_LOG_LEVEL=WARNING \
    LOG_LEVEL=INFO

# www-data
USER 33
