# 1. Challenge Name:

Three Jumps ltd

# 2. Scenario:

Three Jumps Ltd recently completed an infrastructure migration, but some older operational systems and release records were left behind. The company’s internal Inventory Service website is intended to be available only inside its corporate network, while sensitive data is held in a separate zone. You have been given access to a Kali Linux machine on the edge network to perform an authorized assessment. A few legacy services and forgotten artifacts may tell a different story from the company’s intended security boundaries.

# 3. Objective:

Reach the final data server, obtain root-level access within the lab, and recover the challenge flag.

# 4. Difficulty:

Hard

# 5. Prerequisites:

- Basic TCP/IP networking, subnetting, routing, and network segmentation.
- Service discovery and enumeration with tools such as Nmap and netcat.
- Linux command-line usage, file permissions, and reading configuration files.
- FTP and SSH fundamentals, including SSH tunneling or jump-host connections.
- Familiarity with password-hash identification and offline cracking tools such as John the Ripper.
- Basic understanding of Linux `sudo` permissions and local privilege-escalation risks.
- Docker Engine and Docker Compose v2 to run the lab locally.

# 6. Startup Instructions:

Run these commands from the directory containing `compose.yaml`:

```bash
docker compose build --pull
docker compose up -d
docker compose ps
```

The first build requires internet access to download base images and packages. After startup, the lab services communicate over isolated Docker networks.

To stop the lab without removing its containers:

```bash
docker compose stop
```

To start those stopped containers again:

```bash
docker compose start
```

To shut down and remove the lab containers and networks:

```bash
docker compose down --remove-orphans
```

# 7. Connection Information:

Enter the provided Kali Linux attacker machine with:

```bash
docker compose exec attacker bash
```

The attacker container is named `hardv2-attacker` and has the Edge-network address `172.28.10.10`.

| Host | Network addresses | Services |
|---|---|---|
| `jump01` | Edge: `172.28.10.20`; Corporate: `172.28.20.10` | FTP `21`, SSH `22` |
| `app01` | Corporate: `172.28.20.20`; Data: `172.28.30.10` | HTTP `8080`, SSH `22` |
| `db01` | Data: `172.28.30.20` | SSH `22`, PostgreSQL `5432` |
| `router` | Edge: `172.28.10.254`; Corporate: `172.28.20.254`; Data: `172.28.30.254` | Network routing and filtering |

The Inventory Service website is hosted internally on `app01` at port `8080`; it is not published on the Docker host. The Edge, Corporate, and Data networks are isolated, and direct routed traffic between zones is filtered by design. Begin your assessment from the Kali container. No target credentials are provided in this briefing.

# 8. Reset Instructions:

From the project directory, run the included reset script:

```bash
bash scripts/reset-lab.sh
```

Or perform the reset manually:

```bash
docker compose down --remove-orphans
docker compose up -d
```

The lab does not use persistent data volumes, so recreating the containers restores their initial challenge state. To rebuild the images as well, run:

```bash
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d
```

# 9. Flag Format:

`duck{****_******}`
