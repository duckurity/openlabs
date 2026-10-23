# OpenLabs CLI

Player and maintainer guide for the repository `./openlabs` command. The CLI
ships from a git clone only. There is no PyPI package and OpenLabs does not
install Docker or OS packages for you.

Spec detail lives in [contracts/cli-v1.md](https://github.com/Duckurity/openlabs/blob/main/contracts/cli-v1.md).
Platform policy lives in [Platform support tiers](Platform-Support-Tiers).
State and redaction live in [OpenLabs state and logs](OpenLabs-State-and-Logs).

## Bootstrap from a clean clone

```bash
git clone https://github.com/Duckurity/openlabs
cd openlabs
./openlabs --version
```

You need Python 3.12 or newer on `PATH`, Docker Engine with Compose v2, and a
Tier 1 host for the supported lifecycle path. See [Platform support tiers](Platform-Support-Tiers).

## Tier 1 path to ready duck-cross

Run these from the repository root.

```bash
./openlabs setup
./openlabs doctor
./openlabs lab setup duck-cross
```

Open the player URL printed in the output (`http://localhost:8377` when the
default port is free). Work the lab brief, then confirm the environment:

```bash
./openlabs lab verify duck-cross
```

When you finish playing:

```bash
./openlabs lab stop duck-cross
```

To tear down namespaced Docker resources and start again:

```bash
./openlabs lab reset duck-cross
./openlabs lab start duck-cross
```

Use `./openlabs lab list` to see catalog status and blockers for other labs.

## Global flags

| Flag | Effect |
|:---|:---|
| `--json` | Print one `openlabs.command.v1` envelope on stdout. Human text on stderr. |
| `--dry-run` | Resolve work and print the plan. No Docker, lab file, git, or `.openlabs/` state mutation. |
| `--non-interactive` | Never prompt. Fail with `OL-0034` when a mutation needs confirmation. |
| `--port PORT` | Lab commands only. Bind a host port when policy allows. |

Place global flags before the subcommand:

```bash
./openlabs --json --non-interactive lab setup duck-cross
```

## Mutating commands

The table states default side effects, `--dry-run` behavior, and
`--non-interactive` notes. Read-only commands (`doctor` without `--fix`,
`lab status`, `lab list`, `issue explain`) do not appear here.

| Command | Default side effects | `--dry-run` | `--non-interactive` |
|:---|:---|:---|:---|
| `setup` | Runs environment probes. Creates `.openlabs/config.json` when the file is missing and prerequisites pass. Does not rewrite an existing config on later runs. | Lists planned repo-local writes only. Performs no writes. | Prompts before first config write unless you accept the default non-interactive create path. |
| `doctor --fix` | Writes missing `.openlabs/config.json` and refreshes the catalog drift cache under `.openlabs/`. Never changes Docker, system packages, or git metadata. No extra confirmation prompt today. | Lists planned repo-local fixes. Performs none. | Safe. |
| `issue bundle` | Always writes a redacted JSON file under `.openlabs/bundles/`. With `--json`, also returns the bundle inline. Includes invocation, platform summary, docker versions when reachable, and evidence path hints. | Returns the planned path and inline bundle payload. Writes no file. | Safe. Missing Docker leaves docker fields null without internal errors. |
| `lab setup` | Full first-run path on supported labs: preflight, resolve, compose validate, build, start, readiness, verify hook. Updates `.openlabs/state/<lab>.json`. Writes a setup log only when a stage fails mid-run. | Prints planned Docker and state steps. No mutation. | Safe when the lab is supported, tier policy allows guaranteed lifecycle, and preflight passes. |
| `lab start` | Runs namespaced `compose up` for a configured or stopped lab. Updates `.openlabs/state/<lab>.json`. Does not append a per-run log file on success. | Prints planned compose up. No mutation. | Safe when state is consistent. |
| `lab verify` | Runs L0–L6 checks for supported labs (includes reset and second-start cycle when `--level` is omitted). Mutates Docker for build, start, smoke checks, and teardown. Does not edit player files outside the lab tree. | Prints the level plan only. No containers change. | Safe on Tier 1 supported labs. Tier 3 hosts fail with `OL-0035` before mutation. |
| `lab stop` | Stops namespaced containers. Keeps configuration for `lab start`. Updates state. | Prints planned compose stop. No mutation. | Safe. |
| `lab reset` | Runs namespaced `compose down --remove-orphans` for the recorded project. Keeps lab source and state file (lifecycle becomes `configured`). Optional `--volumes` deletes named volumes for that project. | Prints planned down steps including `--volumes` when requested. No mutation. | `lab reset --volumes` requires `--yes` with `--non-interactive` or returns `OL-0034`. |

Reset flags: `lab reset <lab> [--volumes] [--yes]`. Scope is always the OpenLabs
compose project name stored in state, never foreign containers.

For experimental labs, mutating lifecycle commands fail with `OL-0039` unless a
reviewed safe path exists. See [Platform support tiers](Platform-Support-Tiers).

## Issue helpers

Diagnostics use stable `OL-####` ids from `contracts/diagnostics.json`.

```bash
./openlabs issue explain OL-0040
./openlabs issue bundle duck-cross
```

`issue explain` reads the registry locally. `issue bundle` collects redacted
context for bug reports. Neither command opens or updates GitHub issues.

Runtime troubleshooting: [CLI troubleshooting](CLI-Troubleshooting).

## Debugging without the CLI

Maintainers and agents may still call repository scripts directly:

```bash
python3 scripts/validate.py
python3 scripts/check.py labs/web/duck-cross
python3 scripts/prove_reference_lab.py
```

Prefer `./openlabs` for the supported player path. Use scripts when you need
narrow, script-level debugging.

## Legacy compose-only path

You can still start a lab with compose from its directory. That path bypasses
OpenLabs state and lifecycle guarantees. See [Getting Started](Getting-Started).
