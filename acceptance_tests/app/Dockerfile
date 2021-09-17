FROM camptocamp/c2cwsgiutils
LABEL maintainer "info@camptocamp.org"

WORKDIR /app

EXPOSE 8080

ENV SQLALCHEMY_URL=postgresql://www-data:www-data@db:5432/test \
    SQLALCHEMY_URL_SLAVE=postgresql://www-data:www-data@db_slave:5432/test \
    GUNICORN_PARAMS="-b :8080 --worker-class gthread --threads 10 --workers 5"

COPY Pipfile Pipfile.lock /tmp/
# hadolint ignore=DL3003
RUN \
    cd /tmp && \
    pipenv install --system --clear --dev && \
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

# www-data
USER 33
