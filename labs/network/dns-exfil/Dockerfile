FROM python:3.12-alpine
WORKDIR /app
RUN adduser -D labuser
COPY app/ /app
USER labuser
CMD ["python", "-m", "http.server", "8000"]
