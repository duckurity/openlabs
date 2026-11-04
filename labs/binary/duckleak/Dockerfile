FROM python:3.12.15-alpine3.24@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4

WORKDIR /srv
COPY app/ .

USER 65534

EXPOSE 8080
CMD ["python3", "server.py"]
