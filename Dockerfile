FROM ubuntu:18.04
LABEL maintainer "info@camptocamp.org"

COPY requirements.txt docker-requirements.txt /opt/c2cwsgiutils/
RUN apt update && \
    DEV_PACKAGES="libpq-dev python3-dev build-essential python3-dev" && \
    DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends \
        libpq5 \
        python3.6 \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        curl \
        gnupg \
        python3-pkgconfig \
        $DEV_PACKAGES && \
    ln -s pip3 /usr/bin/pip && \
    ln -s python3 /usr/bin/python && \
    apt-get clean && \
    rm -r /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r /opt/c2cwsgiutils/requirements.txt -r /opt/c2cwsgiutils/docker-requirements.txt && \
    apt --purge remove -y $DEV_PACKAGES gcc-7 && \
    apt --purge autoremove -y

COPY . /opt/c2cwsgiutils/
RUN flake8 /opt/c2cwsgiutils && \
    echo "from pickle import *" > /usr/lib/python3.6/cPickle.py && \
    pip3 install --disable-pip-version-check --no-cache-dir -e /opt/c2cwsgiutils && \
    (cd /opt/c2cwsgiutils/ && pytest -vv --cov=c2cwsgiutils --color=yes tests && rm -r tests) && \
    python3 -m compileall -q && \
    python3 -m compileall -q /opt/c2cwsgiutils

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

CMD ["c2cwsgiutils_run"]
