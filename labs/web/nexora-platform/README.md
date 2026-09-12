# Challenge Name

Nexora — Integration & Developer Platform

# Scenario

You have access to Nexora, a SaaS integration and developer platform. Nexora production infrastructure is hosted on Google Cloud Platform.

# Objective

Investigate Nexora's infrastructure and identify a way to reach resources that should not be directly accessible from the public application. .

## Goal

Investigate the Nexora platform and determine whether its integration and developer features can be abused to access unintended internal resources.

# Difficulty

Medium

# Prerequisites

Basic web application reconnaissance, HTTP fundamentals, REST API basics, GraphQL basics, DNS basics, familiarity with server-side requests, and basic Docker/networking knowledge are helpful.

## Brief
 Nexora is a B2B integration and developer platform that allows users to configure external resources, integrations, and webhooks. As part of a security assessment, investigate the platform and determine whether its server-side functionality can be used to reach resources that should not be publicly accessible.

## Setup

Start the challenge with:

```bash
docker compose up --build
```

The main application will be available at:

http://localhost:8080

The local OAST dashboard will be available at:

http://localhost:8081

The challenge is designed to run locally using Docker and does not require external cloud infrastructure or Internet access. 


# Connection Information

Application: http://localhost:8080

OAST: http://localhost:8081

# OAST Service

The challenge includes a local OAST service that you may use to observe DNS and HTTP interactions generated during testing. It is a replareplacement for burp suite collaborator. Open the dashboard to observe interactions.

# Reset Instructions

```sh
docker compose down -v
docker compose up --build
```

# Flag Format

`duck{****_**_*******}`
