FROM camptocamp/python-gis:3.6-stretch
LABEL maintainer "info@camptocamp.org"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        libgeos-dev \
        libproj-dev \
        libjpeg-dev \
        postgresql-client-9.6 \
        graphviz \
        vim && \
    apt-get clean && \
    rm -r /var/lib/apt/lists/*
COPY requirements.txt /opt/c2cwsgiutils/
RUN pip install --no-cache-dir -r /opt/c2cwsgiutils/requirements.txt

COPY . /opt/c2cwsgiutils/
RUN flake8 /opt/c2cwsgiutils && \
    pip install --no-cache-dir -e /opt/c2cwsgiutils && \
    (cd /opt/c2cwsgiutils/ && pytest -vv --color=yes tests && rm -r tests) && \
    python -m compileall -q && \
    python -m compileall -q /opt/c2cwsgiutils

ENV LOG_TYPE=console \
    LOG_HOST=localhost \
    LOG_PORT=514 \
    SQL_LOG_LEVEL=WARN \
    GUNICORN_LOG_LEVEL=WARN \
    OTHER_LOG_LEVEL=WARN \
    DEVELOPMENT=0

CMD ["c2cwsgiutils_run"]
