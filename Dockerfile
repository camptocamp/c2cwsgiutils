FROM ubuntu:20.04 AS base
LABEL maintainer "info@camptocamp.org"

COPY requirements.txt docker-requirements.txt /opt/c2cwsgiutils/
RUN apt update && \
    DEV_PACKAGES="libpq-dev build-essential python3.8-dev" && \
    DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends \
        libpq5 \
        python3.8 \
        curl \
        postgresql-client-12 \
        net-tools iputils-ping screen \
        gnupg \
        $DEV_PACKAGES && \
    DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-pkgconfig && \
    apt-get clean && \
    rm -r /var/lib/apt/lists/* && \
    pip3 install --no-cache-dir -r /opt/c2cwsgiutils/requirements.txt -r /opt/c2cwsgiutils/docker-requirements.txt && \
    strip /usr/local/lib/python3.8/dist-packages/*/*.so && \
    apt remove --purge --autoremove --yes $DEV_PACKAGES binutils

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

CMD ["c2cwsgiutils-run"]


FROM base AS lite
COPY . /opt/c2cwsgiutils/
RUN pip3 install --disable-pip-version-check --no-cache-dir -e /opt/c2cwsgiutils && \
    python3 -m compileall -q && \
    python3 -m compileall /usr/local/lib/python3.8 /usr/lib/python3.8 /opt/c2cwsgiutils -q


FROM lite AS standardbase
COPY requirements-dev.txt /opt/c2cwsgiutils/
RUN python3 -m pip install --no-cache-dir -r /opt/c2cwsgiutils/requirements-dev.txt


FROM standardbase AS standard
COPY . /opt/c2cwsgiutils/
RUN python3 -m compileall -q && \
    python3 -m compileall /usr/local/lib/python3.8 /usr/lib/python3.8 /opt/c2cwsgiutils -q
RUN (cd /opt/c2cwsgiutils/ && flake8) && \
    echo "from pickle import *" > /usr/lib/python3.8/cPickle.py && \
    (cd /opt/c2cwsgiutils/ && pytest -vv --cov=c2cwsgiutils --color=yes tests && rm -r tests)


FROM standard AS full
