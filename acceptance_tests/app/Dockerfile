FROM camptocamp/c2cwsgiutils:latest-full
LABEL maintainer "info@camptocamp.org"

WORKDIR /app

EXPOSE 8080

ENV SQLALCHEMY_URL=postgresql://www-data:www-data@db:5432/test \
    SQLALCHEMY_URL_SLAVE=postgresql://www-data:www-data@db_slave:5432/test \
    GUNICORN_PARAMS="-b :8080 --worker-class gthread --threads 10 --workers 5"

COPY . /app

ARG GIT_HASH

RUN pip3 install --no-cache-dir -e . && \
    ./models_graph.py > models.dot && \
    ./models_graph.py Hello > models_hello.dot && \
    c2cwsgiutils-genversion $GIT_HASH && \
    flake8 c2cwsgiutils_app app_alembic && \
    python3 -m compileall -q .

# www-data
USER 33
