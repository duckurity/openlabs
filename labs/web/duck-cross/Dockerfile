FROM python:3.12-alpine

WORKDIR /srv
COPY app/ .

USER 65534

EXPOSE 8377
CMD ["python3", "server.py"]
