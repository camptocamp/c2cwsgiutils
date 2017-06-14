FROM camptocamp/c2cwsgiutils:latest
LABEL maintainer "info@camptocamp.org"

ARG DOCKER_VERSION=1.12.0
ARG DOCKER_COMPOSE_VERSION=1.10.0

WORKDIR /acceptance_tests

ENV DOCKER_RUN=1 \
    PYTHONPATH=/acceptance_tests

# Install all Debian dependencies except nodejs which requires https transport
COPY  dockerproject.org.asc /acceptance_tests/
RUN echo "deb http://apt.dockerproject.org/repo debian-jessie main" >> /etc/apt/sources.list && \
    echo 'deb http://http.debian.net/debian jessie-backports main' >> /etc/apt/sources.list && \
    apt-key adv --import /acceptance_tests/dockerproject.org.asc && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-engine=${DOCKER_VERSION}*  && \
    apt-get clean && \
    rm -r /var/lib/apt/lists/*

# Install matching docker-compose version
RUN curl -L https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-`uname -s`-`uname -m` > /usr/bin/docker-compose && \
    chmod a+x /usr/bin/docker-compose

COPY . ./

RUN flake8 tests
CMD py.test -vv --color=yes --junitxml /reports/acceptance.xml tests
