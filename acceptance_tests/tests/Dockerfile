FROM camptocamp/c2cwsgiutils:tests
LABEL maintainer "info@camptocamp.org"

ARG DOCKER_VERSION=1.12.0

WORKDIR /acceptance_tests

RUN \
    apt-get update && \
    apt-get install -y docker.io && \
    apt-get clean && \
    rm --force --recursive /var/lib/apt/lists/*

COPY Pipfile Pipfile.lock /tmp/
# hadolint ignore=DL3003
RUN \
    cd /tmp && \
    pipenv sync --system --clear --dev && \
    rm --recursive --force /tmp/* /root/.cache/*

ENV DOCKER_RUN=1 \
    PYTHONPATH=/acceptance_tests

COPY . ./

CMD py.test -vv --color=yes --junitxml /reports/acceptance.xml tests
