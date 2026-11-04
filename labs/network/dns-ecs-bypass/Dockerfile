FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

WORKDIR /app
COPY src/dns_server.py /app/dns_server.py

USER 65534

EXPOSE 5353/udp
CMD ["python3", "-u", "/app/dns_server.py"]
