FROM grahamdumpleton/mod-wsgi-docker:python-3.5
MAINTAINER Camptocamp "info@camptocamp.com"

# Doing things in two steps to avoid needing to re-install everything when we do a rebuild
# after changing code

# Step #1 copy only the stuff needed to install the dependencies and run the script
COPY requirements.txt setup.py /app/
COPY .whiskey /app/.whiskey
RUN mod_wsgi-docker-build

EXPOSE 80

ENV LOG_TYPE console
ENV LOG_HOST localhost
ENV LOG_PORT 514
ENV SQL_LOG_LEVEL WARN
ENV OTHER_LOG_LEVEL WARN
ENV DEVELOPMENT 0

# Step #2 copy the rest of the files (watch for the .dockerignore)
COPY . /app
RUN python /app/setup.py install

CMD ["mod_wsgi-docker-start", "application.wsgi"]
