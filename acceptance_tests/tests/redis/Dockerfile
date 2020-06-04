FROM redis:5

RUN apt-get update && \
    apt-get install --yes curl && \
    apt-get clean

COPY entrypoint /

EXPOSE 26379

ENTRYPOINT ["/entrypoint"]
