#!/bin/bash
# Script used when building acceptance test images to install the docker tools needed to run them.
set -ex

DEBIAN_VERSION=$(grep VERSION= /etc/os-release | sed 's/.*(\(.*\)).\+/\1/')

apt-get update
apt-get install --yes --no-install-recommends apt-transport-https

if [[ "${DEBIAN_VERSION}" == "Bionic Beaver" ]]; then
  DEBIAN_VERSION=stretch
fi

if [[ "${DOCKER_VERSION}" == 1.* ]]; then
  curl -fsSL "https://apt.dockerproject.org/gpg" | apt-key add -
  echo "deb [arch=amd64] https://apt.dockerproject.org/repo debian-${DEBIAN_VERSION} main" >> /etc/apt/sources.list
  PACKAGE=docker-engine
else
  if [[ "${DOCKER_VERSION}" == *-ce ]]; then
    DOCKER_VERSION=${DOCKER_VERSION//\.[0-9]*\.[0-9]*-ce/}
  else
    # The version number is too exotic => use a hardcoded one
    DOCKER_VERSION="17.12"
  fi
  BASE_URL="https://download.docker.com/linux/debian"
  curl -fsSL "${BASE_URL}/gpg" | apt-key add -
  echo "deb [arch=amd64] ${BASE_URL} ${DEBIAN_VERSION} stable" >> /etc/apt/sources.list
  PACKAGE=docker-ce
fi
apt-get update
apt-get install --yes --no-install-recommends ${PACKAGE}=${DOCKER_VERSION}*

curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" > /usr/bin/docker-compose
chmod a+x /usr/bin/docker-compose

apt-get clean
rm -r /var/lib/apt/lists/*
