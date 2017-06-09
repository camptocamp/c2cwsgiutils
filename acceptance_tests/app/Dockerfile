FROM camptocamp/c2cwsgiutils:latest
MAINTAINER Camptocamp "info@camptocamp.com"

# Doing things in two steps to avoid needing to re-install everything when we do a rebuild
# after changing code

# Step #1 copy only the stuff needed to install the dependencies and run the script
WORKDIR /app

EXPOSE 80

ENV SQLALCHEMY_URL=postgresql://www-data:www-data@db:5432/test \
    SQLALCHEMY_URL_SLAVE=postgresql://www-data:www-data@db_slave:5432/test

# Step #2 copy the rest of the files (watch for the .dockerignore)
COPY . /app

ARG GIT_TAG
ARG GIT_HASH

RUN python ./setup.py install && \
    ./models_graph.py > models.dot && \
    ./models_graph.py Hello > models_hello.dot && \
    c2cwsgiutils_genversion.py $GIT_TAG $GIT_HASH && \
    flake8 c2cwsgiutils_app
