# ── Stage 1: Build ────────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/sdk@sha256:f7e28a0a3f6f9235929ec19274fd0ddf8534e9159f99fac602ac73304f1ce99f AS build
WORKDIR /src

COPY VaultCorp.csproj .
RUN dotnet restore

COPY . .
RUN dotnet publish -c Release -o /app/publish --no-restore

# ── Stage 2: Runtime ───────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/aspnet@sha256:1601380775673021a23ea5985669f1daf03719faaa684f839da1752fb48cfc7f AS runtime
WORKDIR /app

# Copy published output
COPY --from=build /app/publish .

# Create persistent data directory (SQLite lives here)
RUN mkdir -p /app/data && chmod 777 /app/data

# wwwroot must be writable — CommandExecutorJob writes output files there
RUN chmod -R 777 /app/wwwroot

# Flag — injected at build time from docker-compose.yml's build arg.
# This default is only a fallback for a bare `docker build` with no
# arg passed; the real value always comes from docker-compose.yml.
ARG FLAG=duck{ogcyy36xyw18n0zh7q10pv8n}
RUN echo "$FLAG" > /app/flag.txt && chmod 444 /app/flag.txt

EXPOSE 5000
ENV ASPNETCORE_URLS=http://+:5000
ENV ASPNETCORE_ENVIRONMENT=Production

RUN useradd --no-create-home --uid 10001 appuser
USER appuser

ENTRYPOINT ["dotnet", "VaultCorp.dll"]
