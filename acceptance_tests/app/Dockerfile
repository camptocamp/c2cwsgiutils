FROM python:3.5
MAINTAINER Camptocamp "info@camptocamp.com"

# Doing things in two steps to avoid needing to re-install everything when we do a rebuild
# after changing code

# Step #1 copy only the stuff needed to install the dependencies and run the script
WORKDIR /app
COPY requirements.txt rel_requirements.txt /app/
RUN pip install -r requirements.txt

EXPOSE 80

ENV LOG_TYPE console
ENV LOG_HOST localhost
ENV LOG_PORT 514
ENV SQL_LOG_LEVEL WARN
ENV OTHER_LOG_LEVEL WARN
ENV DEVELOPMENT 0

# Step #2 copy the rest of the files (watch for the .dockerignore)
COPY . /app

RUN python ./setup.py install && \
    ./models_graph.py > models.dot && \
    ./models_graph.py Hello > models_hello.dot && \
    flake8 c2cwsgiutils c2cwsgiutils_app

CMD ["./c2cwsgiutils_run"]
