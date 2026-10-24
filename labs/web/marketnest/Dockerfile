FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
COPY pom.xml .
COPY src ./src
RUN mvn -q -DskipTests package
RUN gcc -O2 -s -o /app/flagbinary src/main/c/priceforge_flag.c

FROM eclipse-temurin:17-jre
WORKDIR /app
RUN useradd -m ctfuser

COPY --from=build /app/target/priceforge-ctf-1.0.0.jar app.jar
COPY --from=build /app/flagbinary /app/flagbinary
RUN chown -R root:root /app \
    && chmod 555 /app \
    && chmod 644 /app/app.jar \
    && chmod 755 /app/flagbinary

USER ctfuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
