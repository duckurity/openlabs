FROM python:3.12-alpine@sha256:e6dae589c1c05976188fd3bd019afd091445fc533ed2ea29001beddc7368a9c8
WORKDIR /app
RUN adduser -D labuser
COPY app/ /app
USER labuser
CMD ["python", "-m", "http.server", "8000"]
