# OpenLabs contracts

Machine-readable definitions for the OpenLabs lab metadata contract and related
interfaces. Human decisions live in `wiki/M1-Contract-Decisions.md`.

## Lab metadata v1 (`lab.schema.json`)

JSON Schema 2020-12 describes the **structural** shape of a v1 lab record after
flat `lab.yml` is parsed into JSON types. It does not parse YAML and does not
prove repository layout by itself.

### Structural rules (schema)

| Field | Constraint |
|:---|:---|
| `contract_version` | Integer `1` only in M1 |
| `name` | Lowercase hyphenated slug pattern |
| `track` | One of five track enums |
| `difficulty` | One of four difficulty enums |
| `description` | Non-empty string |
| `flag_hash` | 64 lowercase hex digits |
| `status` | `experimental` or `supported` |
| `techniques` | Array of slug patterns; may be empty |
| `checkpoint_flag_hash` | Optional; same pattern as `flag_hash` |
| `port` | Optional integer 1–65535 |
| Unknown keys | Rejected (`additionalProperties: false`) |

### Repository-context rules (not in JSON Schema)

Enforced in `scripts/openlabs_contract.py` and `scripts/validate.py`:

| Rule | Where enforced today |
|:---|:---|
| `name` equals directory basename | `validate_lab_context` / `check_lab` |
| `track` equals parent directory name | `validate_lab_context` / `check_lab` |
| Each `techniques` slug has `content/technique/<slug>.mdx` | `validate_lab_context` / `check_lab` |
| No plaintext `duck{...}` in `lab.yml` or lab `README.md` | `check_lab` |
| Compose file and README sections present | `check_lab` (structure, not schema) |
| `supported` promotion needs L0-L6 proof | `prove_reference_lab.py`, governance docs |

### YAML authoring surface (v1 frozen on main)

The approved flat subset is documented in `wiki/M1-Contract-Decisions.md` and
frozen in `wiki/M1-09-Contract-v1-Freeze.md`. Parsing lives in
`scripts/openlabs_contract.py`. Catalogued labs on `main` declare
`contract_version: 1`.

### Validation command

```bash
python3 scripts/test_contract.py
python3 scripts/test_contract_schema.py
python3 scripts/test_diagnostic_registry.py
```

## Diagnostic registry v1 (`diagnostics.json`)

Stable `OL-####` identifiers map symbolic failure keys to short
summaries. Contract parsers emit `contract.*` keys; the M2 CLI reserves
`lifecycle.*` and `environment.*` keys documented in `contracts/cli-v1.md`.
`scripts/diagnostic_registry.py` loads the file, validates ordering and
uniqueness, and redacts flags, tokens, secrets, and home paths from diagnostic
text. Runtime entries from `OL-0034` onward include explain metadata for
`openlabs issue explain`.

Lookup an id or key in `diagnostics.json`. Contributor-facing summary:
`wiki/M1-09-Contract-v1-Freeze.md`.

## CLI and JSON v1 (`cli-v1.md`)

**Not shipped.** This file specifies future `openlabs` command-line behavior,
exit codes, and the `openlabs.command.v1` JSON envelope. Golden examples live
under `scripts/fixtures/cli_contract/`. Use repository scripts documented in
`AGENTS.md` until the CLI lands in a later milestone.

```bash
python3 scripts/test_cli_contract_fixtures.py
```
