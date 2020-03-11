FROM ubuntu:18.04 AS lite
LABEL maintainer "info@camptocamp.org"

COPY requirements.txt docker-requirements.txt fake_python3 /opt/c2cwsgiutils/
RUN apt update && \
    DEV_PACKAGES="libpq-dev build-essential python3.7-dev equivs" && \
    DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends \
        libpq5 \
        python3.7 \
        curl \
        gnupg \
        $DEV_PACKAGES && \
    equivs-build /opt/c2cwsgiutils/fake_python3 && \
    dpkg -i python3_3.7.1-1~18.04_amd64.deb && \
    rm python3_3.7.1-1~18.04_amd64.deb && \
    ln -s pip3 /usr/bin/pip && \
    ln -s python3.7 /usr/bin/python && \
    ln -sf python3.7 /usr/bin/python3 && \
    DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-pkgconfig && \
    apt-get clean && \
    rm -r /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r /opt/c2cwsgiutils/requirements.txt -r /opt/c2cwsgiutils/docker-requirements.txt && \
    strip /usr/local/lib/python3.7/dist-packages/*/*.so && \
    apt remove --purge --autoremove --yes $DEV_PACKAGES binutils && \
    rm /opt/c2cwsgiutils/fake_python3

COPY . /opt/c2cwsgiutils/
RUN pip3 install --disable-pip-version-check --no-cache-dir -e /opt/c2cwsgiutils && \
    python3 -m compileall -q && \
    python3 -m compileall /usr/local/lib/python3.7 /usr/lib/python3.7 /opt/c2cwsgiutils -q

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


FROM lite AS standard

RUN python3 -m pip install --no-cache-dir -r /opt/c2cwsgiutils/requirements-dev.txt && \
    flake8 /opt/c2cwsgiutils && \
    echo "from pickle import *" > /usr/lib/python3.7/cPickle.py && \
    (cd /opt/c2cwsgiutils/ && pytest -vv --cov=c2cwsgiutils --color=yes tests && rm -r tests) && \
    python3 -m compileall /usr/local/lib/python3.7 -q


FROM standard AS full

RUN . /etc/os-release && \
    apt update && \
    cd /opt/c2cwsgiutils && \
    DEV_PACKAGES="python3.7-dev graphviz-dev build-essential" && \
    DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends curl ca-certificates && \
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    echo "deb http://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt update && \
    DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends \
        graphviz postgresql-client-12 git net-tools iputils-ping screen \
        vim vim-editorconfig vim-addon-manager tree \
        ${DEV_PACKAGES} && \
    vim-addon-manager --system-wide install editorconfig && \
    echo 'set hlsearch  " Highlight search' > /etc/vim/vimrc.local && \
    echo 'set wildmode=list:longest  " Completion menu' >> /etc/vim/vimrc.local && \
    echo 'set term=xterm-256color  " Make home and end working' >> /etc/vim/vimrc.local && \
    pip install --disable-pip-version-check --no-cache-dir -r docker-requirements-full.txt && \
    apt remove --purge --autoremove --yes ${DEV_PACKAGES} binutils && \
    apt-get clean && \
    rm --force --recursive /var/lib/apt/lists/*
