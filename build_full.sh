#!/bin/bash

set -e

GDAL_VERSION=$(sed -ne 's/GDAL==\(.*\)/\1/p' /opt/c2cwsgiutils/docker-requirements-full.txt)
NB_CPUS=`grep -c ^processor /proc/cpuinfo`

apt update

# install the packages needed to build (will be removed at the end)
BUILD_PKG="python3.7-dev libcurl4-openssl-dev libpq-dev libkml-dev libspatialite-dev \
    libopenjp2-7-dev libspatialite-dev libwebp-dev build-essential graphviz-dev"
DEBIAN_FRONTEND=noninteractive apt install --yes --no-install-recommends ${BUILD_PKG}

# download GDAL
curl http://download.osgeo.org/gdal/${GDAL_VERSION}/gdal-${GDAL_VERSION}.tar.gz > /tmp/gdal.tar.gz
tar --extract --file=/tmp/gdal.tar.gz --directory=/tmp

# build GDAL
cd /tmp/gdal-${GDAL_VERSION}
./configure \
    --prefix=/usr \
    --with-python \
    --with-geos \
    --with-geotiff \
    --with-jpeg \
    --with-png \
    --with-expat \
    --with-libkml \
    --with-openjpeg \
    --with-pg \
    --with-curl \
    --with-spatialite \
    --with-openjpeg \
    --with-webp \
    --disable-static
make -j${NB_CPUS}
make -j${NB_CPUS} install
cd /

# remove debug symbols
strip /usr/lib/libgdal.so.*.*.* /usr/bin/ogr* /usr/bin/gdal* || true
pip install --disable-pip-version-check --no-cache-dir -r /opt/c2cwsgiutils/docker-requirements-full.txt

# remove stuff that is not needed anymore
apt remove --purge --yes ${BUILD_PKG}
apt autoremove --purge --yes
apt clean
rm --force --recursive /tmp/* /var/lib/apt/lists/*

# test if we didn't remove too many packages
ogr2ogr --formats
gdalinfo --formats
