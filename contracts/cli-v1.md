# OpenLabs CLI and JSON contract v1

Specification for the `openlabs` player and maintainer CLI (M2). M1-07
introduced the envelope; M2-01 extends commands, lifecycle state, support tiers,
and safety rules. The executable lands in M2-02; repository scripts remain usable
for debugging until the CLI is shipped.

Human decisions live in `wiki/M1-Contract-Decisions.md` and
`wiki/M2-Lifecycle-Decisions.md`. Golden JSON examples live under
`scripts/fixtures/cli_contract/`.

## Global conventions

### Invocation shape

```text
openlabs [--json] [--dry-run] [--non-interactive] [--version] <command> [arguments]
openlabs lab [--port PORT] [--json] [--dry-run] [--non-interactive] <action> <lab> ...
```

| Flag | Behavior |
|:---|:---|
| `--json` | Print one `openlabs.command.v1` envelope on stdout. Human text goes to stderr. |
| `--dry-run` | Resolve targets and print planned work. Must not mutate Docker, lab files, git, or `.openlabs/` state files. |
| `--non-interactive` | Never prompt. Fail with `lifecycle.interaction.non_interactive_required` when a mutation would need confirmation. |
| `--version` | Print CLI version and supported contract markers; exit `0`. |
| `--port` | Lab commands only. Bind the documented host port when free; fail with `lifecycle.port.conflict` when occupied. |

### Exit codes

| Code | Meaning |
|:---:|:---|
| `0` | Success (`ok: true` in JSON mode). |
| `1` | Command failed; blocking errors present. |
| `2` | Usage error (unknown command, missing lab, invalid action). |
| `3` | Environment not ready (Docker client or daemon missing, invalid repo layout). |

JSON mode must still print an envelope when exit code is non-zero.

### Response envelope (`openlabs.command.v1`)

Every `--json` run emits a single JSON object:

| Field | Type | Required | Rules |
|:---|:---|:---:|:---|
| `version` | string | yes | Must be `openlabs.command.v1`. |
| `command` | string | yes | Top-level command name. |
| `ok` | boolean | yes | Mirrors exit code `0` vs non-zero. |
| `exit_code` | integer | yes | Same value as process exit code. |
| `dry_run` | boolean | yes | Reflects `--dry-run`. |
| `data` | object | yes | Command-specific payload; may be `{}`. |
| `diagnostics` | array | yes | Registry-backed findings; empty on full success. |
| `meta` | object | no | `duration_ms`, `redacted`, `reset_safe`, `non_interactive`. |

Each diagnostic item:

| Field | Type | Required |
|:---|:---|:---:|
| `id` | string | yes | `OL-####` from `contracts/diagnostics.json`. |
| `key` | string | yes | Symbolic registry key. |
| `message` | string | yes | Redacted human text. |

### Redaction

CLI output must apply the same redaction rules as `scripts/diagnostic_registry.py`
before writing diagnostics or bundled artifacts: no plaintext flags, no raw
64-char hashes in messages unless explicitly marked `<hash>`, no bearer tokens,
no home-directory paths.

Set `meta.redacted: true` when any diagnostic or bundled field was redacted.

### Reset safety

Commands that stop or remove lab runtime state (`lab reset`, `lab stop` with
teardown policy, `lab prove` L6) must:

- Scope Docker changes to the OpenLabs compose project name recorded in state.
- Never delete the lab directory, git metadata, or player notes outside the lab tree.
- Never invoke Docker-wide prune commands.
- Set `meta.reset_safe: true` when a reset completes without touching out-of-scope paths.

### Support tiers

| Tier | CLI behavior |
|:---|:---|
| Tier 1 | Linux `x86_64`, Python 3.12, Docker Engine, Compose v2: full lifecycle guarantee for `duck-cross`. |
| Tier 2 | WSL2 and macOS with Docker Desktop: detect, diagnose, document next steps; no release guarantee without runner evidence. |
| Tier 3 | Linux ARM64 and Apple Silicon: detect early; run only with explicit per-lab evidence, else `lifecycle.platform.unsupported_architecture`. |
| Unsupported runtime | Podman and similar: detection or guidance only; never assume Docker compatibility. |

### Supported versus experimental labs

| Status | Lifecycle guarantee |
|:---|:---|
| `supported` | `duck-cross` on Tier 1: `lab setup`, `start`, `status`, `verify`, `reset`, `stop` as documented. |
| `experimental` | Appears in `lab list`; may expose blockers (for example explicit `container_name`); mutating lifecycle returns `lifecycle.lab.unsupported_operation` unless a reviewed generic safe path exists. |

Uncatalogued directories under `labs/` are excluded from `lab list` and from
lab selection.

### Repo-local state (`openlabs.state.v1`)

OpenLabs stores operational data under `.openlabs/` (gitignored):

```text
.openlabs/
  config.json
  state/<lab-slug>.json
  logs/<lab>/<run-id>.log
  bundles/<timestamp>.json
```

State file rules:

- Atomic write (temp file plus rename).
- Per-lab lock file during mutating commands.
- No plaintext flags, tokens, credentials, or raw `flag_hash` values.
- Fields include: `version` (`openlabs.state.v1`), `lab`, `compose_project`,
  `host_port`, `lifecycle`, `updated_at`, optional redacted `evidence_path`.

Lifecycle states (stored in `lifecycle`):

| State | Meaning |
|:---|:---|
| `unconfigured` | No durable OpenLabs configuration for this lab. |
| `configured` | Compose project, port, and paths resolved; containers not running. |
| `building` | Image build in progress. |
| `starting` | Containers up; readiness not proven. |
| `ready` | Readiness checks passed; player URL valid. |
| `stopped` | Containers stopped; configuration reusable by `lab start`. |
| `failed` | Last mutation failed; diagnostics and partial evidence preserved. |
| `resetting` | Teardown in progress. |

Recovery: if a command exits on signal or subprocess timeout, the CLI leaves
state in the last honest phase and emits `lifecycle.state.interrupted` with
next actions. A later `lab status` reconciles recorded state with Compose.

### Compose namespacing and ports

- Compose project name is deterministic from repository identity and lab slug
  (length limits per Compose apply).
- Every `docker compose` invocation passes `-f` to the lab compose file and
  `-p` to the OpenLabs project name.
- If a compose file sets `container_name`, lifecycle mutation must fail before
  Docker with `lifecycle.compose.unsafe_container_name`.
- Default port comes from lab metadata or README; when policy allows and the
  port is busy, OpenLabs may select a free loopback port and record it in state.
- `--port` with an occupied port fails with `lifecycle.port.conflict` (no silent
  reassignment).

### Idempotency

| Command | Idempotent behavior |
|:---|:---|
| `setup` (repo) | Re-run checks; no duplicate `.openlabs/` corruption. |
| `lab setup` | If already `ready`, return success with `already_ready` evidence. |
| `lab start` | No-op when already running and ready. |
| `lab status` | Read-only; safe to repeat. |
| `lab stop` | Success when already stopped. |
| `lab reset` | Success when namespaced resources already absent (report no-op). |

## Commands

### `setup`

Repository-level preflight before any lab mutation.

| Action | Default | Purpose |
|:---|:---|:---|
| `run` | yes | Verify repo root, Python, Git, Docker client and daemon, Compose v2, tier classification. |

`data` includes `checks`, `missing`, and `tier`. `--dry-run` lists planned
repo-local writes only (for example `.openlabs/config.json`) without creating them.

### `doctor`

Read-only health checks by default.

| Action | Default | Purpose |
|:---|:---|:---|
| `run` | yes | Aggregate validate, catalog drift, triage, and environment probes. |

`doctor --fix` applies **repo-local** repairs only (cache, generated OpenLabs
config). `--fix --dry-run` lists planned changes and performs none. Maps
conceptually to `validate.py`, `sync_catalog_public.py --check`, and
`lab_triage_inventory.py --check`.

### `issue`

Local diagnostic tooling. Never calls GitHub.

| Action | Default | Purpose |
|:---|:---|:---|
| `explain` | no | Given `OL-####`, return cause, evidence to inspect, safe action, manual action, rollback when defined. |
| `bundle` | yes | Collect redacted diagnostics, versions, and optional lab into `data.bundle` or `.openlabs/bundles/`. |

`explain` sets `data.id`, `data.cause`, `data.evidence`, `data.safe_action`,
`data.manual_action`, optional `data.rollback`. Unknown ids fail with a stable
registry-backed diagnostic.

`bundle` fields match M1; supports `--dry-run` (print path only, no file).

### `lab`

```text
openlabs [--json] [--dry-run] [--non-interactive] [--port PORT] lab <action> <lab>
```

`<lab>` is a catalog slug (for example `duck-cross`) or canonical path
`labs/<track>/<lab>`. Reject ambiguous, uncatalogued, external, or symlink-escape paths before mutation.

#### Lifecycle actions (M2)

| Action | Purpose |
|:---|:---|
| `list` | Catalogued labs with status, track, port, lifecycle eligibility, blockers. |
| `setup` | Full first-run path: preflight, resolve, configure, validate compose, build, start, readiness, verify, print URL. |
| `start` | Start from `configured` or `stopped` using recorded project and port. |
| `status` | Reconcile state file with Compose; report drift. |
| `verify` | Supported verification (L0–L6 semantics for `duck-cross`). |
| `stop` | Stop namespaced project; keep configuration for `start`. |
| `reset` | Remove namespaced project resources per reset safety; volumes preserved unless a documented destructive mode is confirmed. |

`lab setup` performs the complete supported first-run path. `lab start` reuses
resolved state after `stop`.

#### Maintainer and player script actions (retained)

| Action | Maps to | Notes |
|:---|:---|:---|
| `validate` | `scripts/validate.py` on one lab | Metadata and structure. |
| `score` | `scripts/score_lab.py` | Quality score only. |
| `check` | `scripts/check.py` | Flag check; never echo input flag. |
| `compose` | `docker compose config` | L1 compose render. |
| `prove` | `scripts/prove_reference_lab.py` | Supported reference lifecycle proof. |
| `reset` | Compose down for namespaced project | Must satisfy reset safety rules. |

#### `lab list` payload

`data` includes `action: "list"`, `supported`, `experimental`, and `counts`.
Each entry includes `slug`, `path`, `track`, `difficulty`, `status`, `port`,
`compose_file`, `lifecycle_eligible`, and optional `blockers` (for example
`container_name`).

#### L0–L6 lifecycle mapping (`lab verify` / `lab prove`)

Aligned with `scripts/prove_reference_lab.py` and CI **Prove duck-cross L0-L6**:

| Level | Meaning |
|:---|:---|
| `L0` | Required files and catalog metadata valid. |
| `L1` | Compose renders; player port present. |
| `L2` | Image build succeeds. |
| `L3` | Service ready at documented URL. |
| `L4` | Player entry page and public API smoke checks. |
| `L5` | Intended solve path; checker accepts flag without leaking it. |
| `L6` | Teardown removes namespaced resources. |

`lab verify` and `lab prove --json` set `data.levels` to an ordered list of
`{level, ok, seconds, detail}`. Partial runs may pass `--level L3` to stop after
that level.

## Fixture validation

```bash
python3 scripts/test_cli_contract_fixtures.py
python3 scripts/test_diagnostic_registry.py
python3 scripts/test_contract.py
```
