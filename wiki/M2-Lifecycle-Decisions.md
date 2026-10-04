# M2 lifecycle decisions (approved)

Decision record for milestone **M2 - One-command lab lifecycle**. It defines the
one-command player and maintainer workflow, support tiers, safety boundaries, and
the ordered delivery graph. Senior maintainer approval unlocks **M2-02** only
after **M2-01** merges.

- **Entry issue:** [#124 M2-01](https://github.com/duckurity/openlabs/issues/124)
- **Prior milestone:** [#112 M1-09](https://github.com/duckurity/openlabs/issues/112) on `main` at `9824c947662cd74ee3f38a6cedd884dc20211380`
- **Hosted M1 evidence:** [Actions run 36618799944](https://github.com/duckurity/openlabs/actions/runs/36618799944)
- **Catalog at baseline:** 20 catalogued labs (1 `supported`, 19 `experimental`), 5 uncatalogued directories
- **Record status:** **approved** (see [Approval](#approval))

## Outcome

Ship a dependency-free `./openlabs` command that wraps existing scripts where
possible. A clean Tier 1 machine runs `duck-cross` through setup, start, status,
verify, reset, second start, and stop. Every failure returns structured,
redacted `OL-####` diagnostics in `openlabs.command.v1`.

## Product and support boundary

| Topic | Decision |
|:---|:---|
| Supported lab lifecycle | `duck-cross` only (`status: supported`) |
| Experimental labs | Listed; safe generic ops only; no full lifecycle guarantee |
| Uncatalogued directories | Excluded from normal `lab list` |
| Tier 1 | Linux `x86_64`, Python 3.12, Docker Engine, Compose v2: owned evidence |
| Tier 2 | WSL2, macOS + Docker Desktop: detect and guide; no release guarantee without runners |
| Tier 3 | Linux ARM64, Apple Silicon: detect early; run only with per-lab evidence |
| Other runtimes | Podman and similar: detection or guidance only |

## Safety boundary

- Never install Docker, alter system groups, elevate privileges, or change global proxy or firewall settings.
- Default `doctor` is read-only; `--fix` limits changes to repo-local OpenLabs state.
- Every mutation supports `--dry-run`; CI and `--non-interactive` fail instead of prompting.
- Docker mutations use one deterministic OpenLabs Compose project name per repo and lab.
- Never delete unrelated containers, networks, volumes, git data, or player notes.
- Never persist plaintext flags, tokens, credentials, hashes, or sensitive host paths in state, logs, or bundles.

## State layout

```text
.openlabs/
  config.json
  state/<lab>.json
  logs/<lab>/<run-id>.log
  bundles/<timestamp>.json
```

The directory is gitignored. State format: `openlabs.state.v1` with atomic writes,
per-lab locking, and lifecycle states `unconfigured`, `configured`, `building`,
`starting`, `ready`, `stopped`, `failed`, and `resetting` (or a reviewed equivalent).

## Command surface (M2 target)

```text
./openlabs setup
./openlabs doctor [--fix] [--json]
./openlabs issue explain OL-####
./openlabs issue bundle [lab]
./openlabs lab list
./openlabs lab setup duck-cross
./openlabs lab start duck-cross
./openlabs lab status duck-cross
./openlabs lab verify duck-cross
./openlabs lab reset duck-cross
./openlabs lab stop duck-cross
```

`lab setup` runs the full first-run path. `lab start` reuses safe state after a stop.

## Delivery graph

Order matches the reviewed M2 starter package.

| Step | Issue | Depends on | Pull-request focus |
|:---:|:---|:---|:---|
| 1 | [#124 M2-01](https://github.com/duckurity/openlabs/issues/124) | M1 complete | CLI v1 contract delta and golden fixtures |
| 2 | [#125 M2-02](https://github.com/duckurity/openlabs/issues/125) | M2-01 | Executable core and JSON envelope |
| 3 | [#126 M2-03](https://github.com/duckurity/openlabs/issues/126) | M2-02 | Runtime diagnostics, explain, bundle |
| 4 | [#127 M2-04](https://github.com/duckurity/openlabs/issues/127) | M2-02 | Catalog discovery and `lab list` |
| 5 | [#128 M2-05](https://github.com/duckurity/openlabs/issues/128) | M2-03, M2-04 | Preflight, repo `setup`, `doctor` |
| 6 | [#129 M2-06](https://github.com/duckurity/openlabs/issues/129) | M2-04, M2-05 | State, ports, namespacing, `lab setup` |
| 7 | [#130 M2-07](https://github.com/duckurity/openlabs/issues/130) | M2-06 | Start, status, stop, reset |
| 8 | [#131 M2-08](https://github.com/duckurity/openlabs/issues/131) | M2-07 | Verify and shared `duck-cross` proof |
| 9 | [#132 M2-09](https://github.com/duckurity/openlabs/issues/132) | M2-08 | CI and fault gates |
| 10 | [#133 M2-10](https://github.com/duckurity/openlabs/issues/133) | M2-09 | Docs and M2 release evidence |

## Known gaps (baseline)

- No `./openlabs` entry point yet.
- CLI spec lacks M2 lab lifecycle commands until M2-01 lands.
- Registry reserves `OL-0034`..`OL-0041` for lifecycle and environment keys; M2-03 adds explain metadata and detectors.
- `.openlabs/` is not gitignored until M2-06.
- Eight experimental labs declare explicit `container_name`; lifecycle mutation must reject them until lab fixes land.
- Final Tier 1 Docker evidence requires hosted CI (M2-09).

## Non-goals (M2)

- OS package installation, native Windows outside WSL2, Podman parity, PyPI publish, contract v2, lab promotion, GitHub issue submission, MCP tools.

## Approval

| Reviewer | Date | Outcome |
|:---|:---|:---|
| M9nx | 2026-09-29 | Approved M2 milestone setup; active work starts at M2-01 |

Maintainer sign-off on **M2-01** unlocks **M2-02** per [#124](https://github.com/duckurity/openlabs/issues/124).

## Verification (M2 setup)

```bash
python3 scripts/test_contract.py
python3 scripts/validate.py
git diff --check
```

GitHub: milestone **M2 - One-command lab lifecycle** open; label `vector:setup` created; issues **#124** through **#133** opened unassigned.
