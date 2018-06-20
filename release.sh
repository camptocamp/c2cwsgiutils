#!/bin/bash
set -e

VERSION=$1

cd /opt/c2cwsgiutils/
actual_version=$(python3 ./setup.py --version 2> /dev/null)

if [[ "${VERSION}" != "${actual_version}" ]]
then
    echo "Version mismatch: ${VERSION} != ${actual_version}"
    exit 1
fi

if curl --silent --fail "https://pypi.org/project/c2cwsgiutils/${VERSION}/" > /dev/null
then
    echo "Already released ${VERSION}"
    exit 0
fi

python3 ./setup.py bdist_wheel

pip install twine==1.11.0

twine upload -u "${USERNAME}" -p "${PASSWORD}" dist/*.whl
