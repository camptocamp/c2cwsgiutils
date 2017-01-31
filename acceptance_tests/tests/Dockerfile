FROM python:3.5

ARG DOCKER_VERSION=1.12.0
ARG DOCKER_COMPOSE_VERSION=1.10.0

WORKDIR /acceptance_tests

# Install all Debian dependencies except nodejs which requires https transport
RUN echo "deb http://apt.dockerproject.org/repo debian-jessie main" >> /etc/apt/sources.list && \
    echo 'deb http://http.debian.net/debian jessie-backports main' >> /etc/apt/sources.list && \
    apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D && \
    apt-get update && \
    apt-get install -y docker-engine=${DOCKER_VERSION}* libpq-dev postgresql-client  && \
    apt-get clean && \
    rm -r /var/lib/apt/lists/*

# Install matching docker-compose version
RUN curl -L https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-`uname -s`-`uname -m` > /usr/bin/docker-compose && \
    chmod a+x /usr/bin/docker-compose

# Install python requirements
COPY requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

COPY . ./

ENV DOCKER_RUN 1
ENV PYTHONPATH /acceptance_tests
CMD py.test -vv --color=yes --junitxml /reports/acceptance.xml tests
