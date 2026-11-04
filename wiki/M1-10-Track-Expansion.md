# M1-10 track registry expansion

Decision record for the additive OpenLabs track expansion approved in
[issue #184](https://github.com/duckurity/openlabs/issues/184).

- **Baseline reviewed:** `main` at `6c99e68`, fetched on 2026-10-24
- **Record status:** **approved**
- **Contract marker:** `contract_version: 1`

## Decision

| Item | Approved choice |
|:---|:---|
| Track slugs | `forensics` and `misc` |
| Display label | `Miscellaneous` for `misc` |
| Version policy | Additive v1 enum expansion. No v2 migration. |
| Canonical registry | `contracts/tracks.json` |
| Python loader | `scripts/tracks.py` |
| Parity gate | `scripts/test_track_registry.py` |
| Delivery | Contract support first. One experimental lab per later pull request. |

The v1 flat YAML shape does not change. Existing labs keep their metadata,
paths, flags, ports, status, and difficulty. The M1-09 freeze remains the
record for the v1 shape. This record approves two additional `track` values.

## Track definitions

| Slug | Label | Focus |
|:---|:---|:---|
| `forensics` | Forensics | memory and disk analysis, artifact recovery, anti-forensics |
| `misc` | Miscellaneous | constrained environments, escape logic, host-level puzzles |

Use `misc` for constrained-environment and escape-style labs. Do not use it as
a catch-all. Redirect a lab when `web`, `binary`, `crypto`, `network`, `osint`,
or `forensics` names its primary weakness.

## Consumer alignment

Python validators and the PDF generator load the canonical registry through
`scripts/tracks.py`. The standalone JSON Schema keeps an explicit enum. The
site keeps one explicit typed tuple. The parity gate compares both explicit
copies with the registry. The Lab idea form uses the same ordered slugs.

Add a track through the registry, schema, typed site tuple, issue form, docs,
and fixtures in one pull request. Run the parity gate before review.

## Verification

```bash
python3 scripts/test_contract.py
python3 scripts/test_track_registry.py
python3 scripts/validate_issue_forms.py
python3 scripts/validate.py
python3 scripts/sync_catalog_public.py --check
OPENLABS_SYNC_HERMETIC=1 python3 scripts/sync_site_content.py --check
pnpm run build
git diff --check
```

No lab directories belong in the track expansion pull request. New labs start
as `experimental`. Promotion still requires L0-L6 evidence.

## Approval

| Reviewer | Date | Outcome |
|:---|:---|:---|
| M9nx | 2026-10-24 | Approved `forensics`, `misc`, additive v1, the canonical registry, and the pull request sequence in issue #184 |
