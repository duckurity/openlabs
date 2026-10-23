## Requirements

- Docker with Compose v2
- Python 3.12 or newer for `./openlabs` and the flag checker
- Tier 1 Linux `x86_64` for the supported lifecycle path (see [Platform support tiers](Platform-Support-Tiers))

## Solve your first lab (supported path)

Use the OpenLabs CLI from the repository root. Full detail: [OpenLabs CLI](OpenLabs-CLI).

1. Clone and enter the repo.

   ```bash
   git clone https://github.com/Duckurity/openlabs
   cd openlabs
   ./openlabs setup
   ./openlabs doctor
   ./openlabs lab setup duck-cross
   ```

2. Open the player URL from the command output (`http://localhost:8377` when the
   default port is free). Work the brief under `labs/web/duck-cross/README.md`.

3. Verify the lab environment and check your solve.

   ```bash
   ./openlabs lab verify duck-cross
   python3 scripts/check.py labs/web/duck-cross
   ```

The checker hashes your input with SHA-256 and compares it against
`flag_hash` in `lab.yml`. It prints `solved` or `not solved`.

When you finish:

```bash
./openlabs lab stop duck-cross
```

## Legacy compose-only path

For debugging without OpenLabs state, start compose from the lab directory:

```bash
cd openlabs/labs/web/duck-cross
docker compose up -d
```

This path does not use lifecycle guarantees. Prefer [OpenLabs CLI](OpenLabs-CLI)
on Tier 1.

## Finding labs

Labs live under `labs/`, grouped by [track](Tracks-and-Difficulty):

```
labs/
├── web/
├── binary/
├── crypto/
├── network/
└── osint/
```

Run `./openlabs lab list` for catalog status and blockers. Only `duck-cross` is
`supported` for the full lifecycle at M2 release.

Each lab directory holds a `README.md` brief. Start with an `easy` lab to
learn the loop, then move up.

## Ports

Each lab documents one host port in its brief. `duck-cross` serves
`http://localhost:8377`. On the CLI path, use `--port` when policy allows or
free the default port. On the legacy path, edit the host side of the mapping in
`docker-compose.yml`. The container port stays fixed.

## Shift the difficulty

Labs are graded from `easy` to `insane`. See
[Tracks and Difficulty](Tracks-and-Difficulty) for the full rubric.

## Stuck?

- Run `./openlabs issue explain OL-####` for registry-backed diagnostics.
- Read [CLI troubleshooting](CLI-Troubleshooting).
- Read the lab brief again. The goal is stated plainly.
- Read the lab source. Open labs work that way.
- Write up your path. The act of explaining often exposes the next step.

A flag you found by reading the code is a flag you earned. The point is the
gap between what the service intends and what it allows.
