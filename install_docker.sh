#!/bin/bash
# Script used when building acceptance test images to install the docker tools needed to run them.
set -e

DEBIAN_VERSION=`grep VERSION= /etc/os-release | sed 's/.*(\(.*\)).\+/\1/'`

apt-get update
apt-get install -y --no-install-recommends apt-transport-https

if [[ ${DOCKER_VERSION} == *-ce ]]
then
    DOCKER_VERSION=$(echo "${DOCKER_VERSION}" | sed -e 's/\.[0-9]*\.[0-9]*-ce//')
    BASE_URL="https://download.docker.com/linux/debian"
    curl -fsSL "${BASE_URL}/gpg" | apt-key add -
    echo "deb [arch=amd64] ${BASE_URL} ${DEBIAN_VERSION} stable" >> /etc/apt/sources.list
    PACKAGE=docker-ce
else
    curl -fsSL "https://apt.dockerproject.org/gpg" | apt-key add -
    echo "deb [arch=amd64] https://apt.dockerproject.org/repo debian-${DEBIAN_VERSION} main" >> /etc/apt/sources.list
    PACKAGE=docker-engine
fi
apt-get update
apt-get install -y --no-install-recommends ${PACKAGE}=${DOCKER_VERSION}*

curl -L https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-`uname -s`-`uname -m` > /usr/bin/docker-compose
chmod a+x /usr/bin/docker-compose

apt-get clean
rm -r /var/lib/apt/lists/*
