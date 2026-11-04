FROM verdaccio/verdaccio:6.7.4

USER root

COPY config.yaml /verdaccio/conf/config.yaml
COPY seed /seed
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && \
    chown -R 10001:65533 /seed

USER verdaccio

EXPOSE 4873

ENTRYPOINT ["/entrypoint.sh"]
