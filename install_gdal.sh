#!/bin/bash -ex
# Script used to install GDAL in child images.

DEV_PACKAGES="python3.8-dev libgdal-dev libcpl-dev build-essential"

apt update

DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends \
    gdal-bin ${DEV_PACKAGES}

GDAL_VERSION=$(dpkg -s gdal-bin | sed -ne 's/^Version: \([^.]*\.[^.]*\.[^.+]*\).*/\1/p')

CPLUS_INCLUDE_PATH=/usr/include/gdal C_INCLUDE_PATH=/usr/include/gdal \
    pip install --disable-pip-version-check --no-cache-dir GDAL==${GDAL_VERSION}

apt remove --purge --autoremove --yes ${DEV_PACKAGES} binutils
apt-get clean
rm --force --recursive /var/lib/apt/lists/*
