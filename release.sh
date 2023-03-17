#!/bin/bash -e

VERSION=$1

cd /opt/c2cwsgiutils/
actual_version=$(python3 ./setup.py --version 2> /dev/null)

if [[ "${VERSION}" != "${actual_version}" ]]; then
  echo "Version mismatch: ${VERSION} != ${actual_version}"
  exit 1
fi

if curl --silent --fail "https://pypi.org/project/c2cwsgiutils/${VERSION}/" > /dev/null; then
  echo "Already released ${VERSION}"
  exit 0
fi

pip install -r publish-requirements.txt

python3 ./setup.py bdist_wheel

if twine upload -u "${USERNAME}" -p "${PASSWORD}" dist/*.whl; then
  echo "Upload to pypi successful"
else
  # maybe it was uploaded at the same time by another job
  if curl --silent --fail "https://pypi.org/project/c2cwsgiutils/${VERSION}/" > /dev/null; then
    echo "Already released ${VERSION} in another job"
    exit 0
  else
    exit 1
  fi
fi
