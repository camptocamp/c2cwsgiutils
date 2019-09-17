FROM camptocamp/c2cwsgiutils:latest-lite

RUN python3 -m pip install --no-cache-dir -r /opt/c2cwsgiutils/requirements-dev.txt && \
    flake8 /opt/c2cwsgiutils && \
    echo "from pickle import *" > /usr/lib/python3.7/cPickle.py && \
    (cd /opt/c2cwsgiutils/ && pytest -vv --cov=c2cwsgiutils --color=yes tests && rm -r tests) && \
    python3 -m compileall /usr/local/lib/python3.7 -q
