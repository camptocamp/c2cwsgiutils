FROM ubuntu:20.04 AS base-all
LABEL maintainer "info@camptocamp.org"

COPY Pipfile* /opt/c2cwsgiutils/
RUN apt update && \
    DEV_PACKAGES="libpq-dev build-essential python3-dev" && \
    DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends \
        libpq5 \
        python3 \
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
    python3 -m pip install --no-cache-dir pipenv && \
    (cd /opt/c2cwsgiutils/ && pipenv install --system --clear) && \
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


FROM base-all AS base-lint
RUN (cd /opt/c2cwsgiutils/ && pipenv install --system --clear --dev)


FROM base-all AS base

CMD ["c2cwsgiutils-run"]

COPY setup.py setup.cfg c2cwsgiutils-run /opt/c2cwsgiutils/
COPY c2cwsgiutils /opt/c2cwsgiutils/c2cwsgiutils
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir --no-deps \
        --editable=/opt/c2cwsgiutils && \
    python3 -m compileall -q && \
    python3 -m compileall /usr/local/lib/python3.8 /usr/lib/python3.8 /opt/c2cwsgiutils -q && \
    python3 -m pip freeze && \
    python3 -c 'import c2cwsgiutils'


FROM base-lint as tests

COPY . /opt/c2cwsgiutils/
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir --no-deps \
        --editable=/opt/c2cwsgiutils
RUN (cd /opt/c2cwsgiutils/ && prospector)
RUN echo "from pickle import *" > /usr/lib/python3.8/cPickle.py
RUN (cd /opt/c2cwsgiutils/ && pytest -vv --cov=c2cwsgiutils --color=yes tests && rm -r tests)


FROM base as standard
