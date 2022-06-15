FROM camptocamp/c2cwsgiutils:tests
LABEL maintainer "info@camptocamp.org"

WORKDIR /acceptance_tests

ENV DOCKER_RUN=1 \
  PYTHONPATH=/acceptance_tests

RUN --mount=type=cache,target=/var/lib/apt/lists \
  --mount=type=cache,target=/var/cache,sharing=locked \
  --mount=type=cache,target=/root/.cache \
  apt-get update \
  && apt-get install --yes --no-install-recommends docker.io \
  && python3 -m pip install docker-compose

COPY . ./

CMD [ "tail", "--follow", "/dev/null" ]
