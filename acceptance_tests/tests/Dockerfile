FROM camptocamp/c2cwsgiutils:tests
LABEL maintainer "info@camptocamp.org"

ARG DOCKER_VERSION=1.12.0

WORKDIR /acceptance_tests

ENV DOCKER_RUN=1 \
    PYTHONPATH=/acceptance_tests

COPY install-docker /opt/c2cwsgiutils/
# Install all Debian dependencies except nodejs which requires https transport
RUN DOCKER_VERSION=${DOCKER_VERSION} \
    /opt/c2cwsgiutils/install-docker

COPY . ./

CMD py.test -vv --color=yes --junitxml /reports/acceptance.xml tests
