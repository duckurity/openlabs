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
| `setup` | Runs environment probes. May create or update `.openlabs/config.json` after checks pass. | Lists planned repo-local writes only. Performs no writes. | Safe when no confirmation is required. |
| `doctor --fix` | Applies repo-local repairs only (OpenLabs cache and config). Never changes Docker, system packages, or git metadata. | Lists planned repairs. Performs none. | Fails with `OL-0034` if a fix would need confirmation. |
| `issue bundle` | Writes a redacted JSON bundle under `.openlabs/bundles/` (or returns inline in `--json`). | Prints the target path or inline plan. Writes no file. | Safe. |
| `lab setup` | Resolves port and compose project, validates compose, builds, starts, and readiness-checks the lab. Updates `.openlabs/state/<lab>.json` and logs. | Resolves targets and prints planned Docker and state steps. No mutation. | Safe when the lab is supported and preflight passes. |
| `lab start` | Starts containers for a configured or stopped lab using recorded project and port. Updates state and logs. | Prints planned compose up steps. No mutation. | Safe when state is consistent. |
| `lab verify` | Runs supported verification levels for the lab (L0–L6 semantics for `duck-cross`). May touch runtime for checks. Read-only to player data outside the lab tree. | Prints levels that would run. Does not start verification unless the implementation treats verify as read-only plan only; prefer `--json` dry-run output for the exact plan. | Safe for supported labs. |
| `lab stop` | Stops namespaced containers. Keeps configuration for a later `lab start`. Updates state. | Prints planned compose stop. No mutation. | Safe. |
| `lab reset` | Removes namespaced compose resources for the lab. Scoped to the OpenLabs project in state. Updates state. Does not delete the lab directory or git data. | Prints planned teardown steps. No mutation. | Fails with `OL-0034` when policy requires confirmation for destructive teardown. |

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
