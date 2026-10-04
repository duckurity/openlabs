# M1 contract v1 freeze

Completion record for milestone **M1 - OpenLabs contract**. It publishes
authoring and migration guidance and freezes `contract_version: 1` on `main`.

- **Issue:** [#112 M1-09](https://github.com/duckurity/openlabs/issues/112)
- **Parent:** [#104 M1-01](https://github.com/duckurity/openlabs/issues/104)
- **Baseline reviewed:** `main` at merge of [#121 M1-08](https://github.com/duckurity/openlabs/pull/121)
- **Record status:** **frozen** (see [Freeze approval](#freeze-approval))

## What is frozen

| Item | Path or rule |
|:---|:---|
| Contract marker | `contract_version: 1` on every catalogued `lab.yml` |
| Schema | `contracts/lab.schema.json` |
| Parser and model | `scripts/openlabs_contract.py` |
| Diagnostics | `contracts/diagnostics.json` (`OL-####` ids) |
| CLI specification | `contracts/cli-v1.md` (spec only; no shipped `openlabs` binary) |
| CI gate | `python3 scripts/test_contract.py` in **Validate labs** |

Decision detail lives in [M1 contract decisions](M1-Contract-Decisions). Open lab
branches still use [M1-06 open lab PR migration](M1-06-Open-Lab-PR-Migration).

## Authoring checklist

Copy `labs/_template/` and set every required key in `lab.yml`:

- `contract_version`, `name`, `track`, `difficulty`, `description`, `flag_hash`,
  `status`, `techniques` (may be `[]`)
- Optional: `checkpoint_flag_hash`, `port`
- Reject any other top-level key in strict validation

Run before you open a pull request:

```bash
python3 scripts/validate.py
python3 scripts/test_contract.py
```

## Diagnostic lookup

Parse and validation failures emit stable ids from `contracts/diagnostics.json`.
Each entry maps a symbolic key (for example `contract.parse.unknown_field`) to
`OL-####` and a short summary.

Lookup:

```bash
python3 -c "import json; d=json.load(open('contracts/diagnostics.json')); print([e for e in d['entries'] if e['key']=='contract.parse.unknown_field'])"
```

Or search the file for the `OL-` id printed in CI or validator output.

`scripts/diagnostic_registry.py` loads the registry and **redacts** plaintext
flags (`duck{...}`), 64-character hex hashes, bearer tokens, common secret
patterns, and home directory paths before diagnostics appear in logs or JSON
reports. Do not bypass redaction when surfacing errors to players.

## CLI status

`contracts/cli-v1.md` and `scripts/fixtures/cli_contract/` define a future
`openlabs` CLI. The repository does **not** ship that command today. Use
`scripts/validate.py`, `scripts/check.py`, and the other paths listed in
`AGENTS.md` until a later milestone adds the CLI.

## CI evidence

Required check on pull requests: **CI required** (`labs.yml` job `ci-required`).

M1 delivery merged on `main`:

| Issue | Pull request | Topic |
|:---|:---|:---|
| M1-02 #105 | [#114](https://github.com/duckurity/openlabs/pull/114) | JSON Schema |
| M1-03 #106 | [#115](https://github.com/duckurity/openlabs/pull/115) | Shared parser |
| M1-04 #107 | [#116](https://github.com/duckurity/openlabs/pull/116) | Consumer migration |
| M1-05 #108 | [#118](https://github.com/duckurity/openlabs/pull/118) | Diagnostics |
| M1-06 #109 | [#119](https://github.com/duckurity/openlabs/pull/119) | Lab metadata migration |
| M1-07 #110 | [#120](https://github.com/duckurity/openlabs/pull/120) | CLI spec |
| M1-08 #111 | [#121](https://github.com/duckurity/openlabs/pull/121) | CI conformance gate |

After this issue merges, confirm the latest **labs** workflow on `main` is green
and branch protection still requires **CI required**.

## Verification (M1-09)

```bash
python3 scripts/test_contract.py
python3 scripts/validate.py
python3 scripts/sync_catalog_public.py --check
OPENLABS_SYNC_HERMETIC=1 python3 scripts/sync_site_content.py --check
python3 scripts/test_baseline_report.py
git diff --check
```

Documentation-only changes must not alter generated catalog or site output.

## Freeze approval

| Reviewer | Date | Outcome |
|:---|:---|:---|
| M9nx | 2026-09-29 | Frozen contract v1 on `main`; contributor docs aligned with schema |

Maintainer sign-off closes milestone **M1** per [#104](https://github.com/duckurity/openlabs/issues/104).
Follow-on work is tracked under milestone **M2 - One-command lab lifecycle** in
[M2 lifecycle decisions](M2-Lifecycle-Decisions) ([#124 M2-01](https://github.com/duckurity/openlabs/issues/124)).
