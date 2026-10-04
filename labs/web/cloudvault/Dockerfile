# Root Dockerfile for the cloudvault lab.
#
# This is a multi-service lab -- the real build targets live under
# app/*/Dockerfile and are wired up in docker-compose.yml. This file
# exists so lab tooling that expects a single Dockerfile at the lab
# root has something to find. It does not run the challenge.

FROM python:3.12-slim

WORKDIR /srv

# Nothing to copy -- the challenge runs via docker compose.
# Match the template convention: run as unprivileged nobody.
USER 65534

CMD ["python3", "-c", "print('cloudvault is a multi-service lab. Run: docker compose up -d')"]
