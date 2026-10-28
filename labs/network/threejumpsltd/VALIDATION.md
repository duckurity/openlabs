# Validation notes

Static checks completed for this bundle:

- `compose.yaml` parses with no duplicate YAML keys.
- All Dockerfile `COPY` sources exist in their respective build contexts.
- All configured static IP addresses are unique.
- No service publishes a port to the host.
- Shell scripts and Dockerfile `RUN` shell snippets pass syntax parsing.
- The archived SHA-512 crypt hash matches the intended `Harbor2026!` candidate.
- A local test archive contains `handover.txt`, `shadow.bak`, and `password-candidates.txt`.

The authoring environment did not have the Docker CLI/daemon, so image builds, live networking, SSH proxying, PostgreSQL startup, and container-recreation reset could not be executed here. Please run the included runtime smoke test on a machine with Docker Compose v2:

```bash
bash scripts/smoke-test.sh
```

The script builds/starts the project, waits for container health checks, tests Nmap and the exposed Edge ports, confirms direct routed access is filtered, checks app-to-PostgreSQL reachability, validates the flag, then destroys and recreates the containers and checks that the privilege-escalation script is restored to its clean state.

If a check fails, inspect the service logs with:

```bash
docker compose logs --tail=100 router attacker jump01 app01 db01
```
