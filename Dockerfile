FROM python:3.6
LABEL maintainer "info@camptocamp.org"

RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main" > /etc/apt/sources.list.d/postgres.list && \
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        libgeos-dev \
        libproj-dev \
        libjpeg-dev \
        postgresql-client-9.5 \
        graphviz \
        vim && \
    apt-get clean && \
    rm -r /var/lib/apt/lists/*
COPY requirements.txt /c2cwsgiutils/
RUN pip install --no-cache-dir -r /c2cwsgiutils/requirements.txt

COPY . /c2cwsgiutils/
RUN flake8 /c2cwsgiutils && \
    pip install --no-cache-dir -e /c2cwsgiutils && \
    (cd /c2cwsgiutils/ && pytest -vv --color=yes tests && rm -r tests)

ENV LOG_TYPE=console \
    LOG_HOST=localhost \
    LOG_PORT=514 \
    SQL_LOG_LEVEL=WARN \
    OTHER_LOG_LEVEL=WARN \
    DEVELOPMENT=0

CMD ["c2cwsgiutils_run"]
