FROM python:3.6

RUN apt-get update && \
    apt-get install -y libpq-dev libgeos-dev libproj-dev libjpeg-dev postgresql-client graphviz: && \
    apt-get clean && \
    rm -r /var/lib/apt/lists/*
COPY rel_requirements.txt /c2cwsgiutils/
RUN pip install --no-cache-dir -r /c2cwsgiutils/rel_requirements.txt

COPY . /c2cwsgiutils/
RUN flake8 /c2cwsgiutils && \
    pip install --no-cache-dir -e /c2cwsgiutils && \
    (cd /c2cwsgiutils/ && pytest -vv tests && rm -r tests)

ENV LOG_TYPE=console \
    LOG_HOST=localhost \
    LOG_PORT=514 \
    SQL_LOG_LEVEL=WARN \
    OTHER_LOG_LEVEL=WARN \
    DEVELOPMENT=0

CMD ["c2cwsgiutils_run"]
