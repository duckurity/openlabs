FROM alpine:3.22
RUN apk add --no-cache iproute2 iptables
COPY router-entrypoint.sh /usr/local/sbin/router-entrypoint.sh
RUN chmod 0755 /usr/local/sbin/router-entrypoint.sh
ENTRYPOINT ["/usr/local/sbin/router-entrypoint.sh"]
