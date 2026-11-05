FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY app/ /usr/share/nginx/html/
COPY README.md /usr/share/nginx/html/README.md
USER 101
EXPOSE 8080
