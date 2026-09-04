## Requirements

- Docker with Compose v2
- `python3` for the flag checker

## Solve your first lab

1. Clone the repository and enter a lab.

   ```bash
   git clone https://github.com/Duckurity/openlabs
   cd openlabs/labs/web/duck-cross
   docker compose up -d
   ```

2. Open the service in your browser and work the brief. The brief under the
   lab directory states the setup and the goal.

3. Return to the repo root. Check the solve.

   ```bash
   cd openlabs
   python3 scripts/check.py labs/web/duck-cross
   ```

The checker hashes your input with SHA-256 and compares it against
`flag_hash` in `lab.yml`. It prints `solved` or `not solved`.

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

Each lab directory holds a `README.md` brief. Start with an `easy` lab to
learn the loop, then move up.

## Ports

Each lab documents one host port in its brief. `duck-cross` serves
`http://localhost:8377`. If a host port is taken, edit the host side of the
mapping in `docker-compose.yml`. The container port stays fixed.

## Shift the difficulty

Labs are graded from `easy` to `insane`. See
[Tracks and Difficulty](Tracks-and-Difficulty) for the full rubric.

## Stuck?

- Read the lab brief again. The goal is stated plainly.
- Read the lab source. Open labs work that way.
- Write up your path. The act of explaining often exposes the next step.

A flag you found by reading the code is a flag you earned. The point is the
gap between what the service intends and what it allows.
