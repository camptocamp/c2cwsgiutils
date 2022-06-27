FROM camptocamp/c2cwsgiutils:tests
LABEL maintainer "info@camptocamp.org"

WORKDIR /acceptance_tests

ENV DOCKER_RUN=1 \
  PYTHONPATH=/acceptance_tests

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends docker.io \
  && apt-get clean \
  && rm -r /var/lib/apt/lists/* \
  && python3 -m pip install docker-compose

COPY . ./

CMD py.test -vv --color=yes --junitxml /reports/acceptance.xml tests
