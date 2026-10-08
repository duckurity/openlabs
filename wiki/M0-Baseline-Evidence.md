## Purpose

Auditable M0 completion record for [#72](https://github.com/duckurity/openlabs/issues/72) (M0-09). Use it before enabling branch protection on `main`. Depends on [#71](https://github.com/duckurity/openlabs/issues/71) (**CI required**).

Reviewed on `2026-10-08`. Regenerate with `python3 scripts/baseline_report.py --write-wiki wiki/M0-Baseline-Evidence.md`. Write `--json` when you need the reviewed git commit and full inventory snapshot.

## Catalog manifest

- Supported: **1**
- Experimental: **19**
- Invalid status: **0**
- Uncatalogued directories: **5**

## Supported manifest

At least one lab must be the verified reference (`duck-cross`).

| Path | Name | Validates | Reference |
|:---|:---|:---:|:---:|
| `labs/web/duck-cross` | duck-cross | yes | yes |

## Validation results

- Inventory exit code: **0** (0 means supported catalog is non-empty and no blocking failures).
- Blocking supported failures: **0**
- Advisory experimental findings: **0**

```bash
python3 scripts/validate.py --json validate-report.json
python3 scripts/score_lab.py --min 70 --json score-report.json
```

## Platform evidence

- Reference lab: `labs/web/duck-cross`
- Lifecycle script: `scripts/prove_reference_lab.py`
- CI job: **Prove duck-cross L0-L6**
- Platform: Linux x86_64 with Docker Compose v2

Run the script locally or read CI artifacts; this report does not start containers.

## Known blockers

### Uncatalogued directories

- `labs/web/Sayed_Khashana_REST_API_IDOR_CTF`
- `labs/web/duckcorp-savegame`
- `labs/web/duckdesk`
- `labs/web/duckfleet`
- `labs/web/duckmarket`

### Experimental labs (not promoted)

- `labs/web/aegis-ctf` (validates)
- `labs/web/cafe-house-rules` (validates)
- `labs/web/cloudvault` (validates)
- `labs/web/duck-nest` (validates)
- `labs/web/duckexchange` (validates)
- `labs/web/duckrpc-archive` (validates)
- `labs/web/duckvault` (validates)
- `labs/web/duckvault-web-ctf` (validates)
- `labs/web/fieldops-360` (validates)
- `labs/web/firmdrama` (validates)
- `labs/web/invoiceportal` (validates)
- `labs/web/nexora-platform` (validates)
- `labs/web/shopvault` (validates)
- `labs/web/snapconnect` (validates)
- `labs/web/snapsync` (validates)
- `labs/web/switf01-hit3` (validates)
- `labs/web/techvault` (validates)
- `labs/web/threadline` (validates)
- `labs/web/vault-api` (validates)

### Triage follow-ups (from M0-05)

Directories inventoried: **25**. Uncatalogued: **5**.

- M0-05 follow-up: rename and catalog Sayed Khashana REST IDOR lab
- M0-05 follow-up: compose and lab.yml for duckcorp-savegame or approved removal
- M0-05 follow-up: catalog duckdesk as experimental
- M0-05 follow-up: L0-L6 review for duckexchange promotion
- M0-05 follow-up: catalog duckfleet as experimental
- M0-05 follow-up: catalog duckmarket as experimental
- M0-05 follow-up: raise invoiceportal score hygiene (optional)
- M0-05 follow-up: snapconnect techniques and docs score pass
- M0-05 follow-up: snapsync techniques and Dockerfile score pass

## Local commands matching CI

Run these from a clean checkout when reproducing **CI required** scope on `main`.

### Validate labs

```bash
python3 scripts/validate.py
python3 scripts/test_m2.py
python3 scripts/test_contract.py
python3 scripts/test_validate_status.py
python3 scripts/test_status_aware_inventory.py
python3 scripts/test_lab_triage_inventory.py
python3 scripts/test_sync_catalog_public.py
python3 scripts/test_ci_routing_matrix.py
python3 scripts/test_baseline_report.py
python3 scripts/baseline_report.py --check
```

### Validate compose files (when in scope)

```bash
python3 scripts/validate.py --compose
```

### Prove duck-cross L0-L6

```bash
python3 scripts/prove_reference_lab.py --json reference-lab-evidence-raw.json
python3 scripts/evidence_artifact.py bound reference-lab-evidence-raw.json reference-lab-evidence.json
python3 scripts/run_m2_tier1_lifecycle.py --json m2-tier1-lifecycle-evidence.json
```

### Security scan

```bash
gitleaks detect --source . --config .gitleaks.toml --redact --verbose
python3 scripts/score_lab.py --min 70 --json score-report.json
```

### Content contracts

```bash
python3 scripts/sync_catalog_public.py --check
python3 scripts/sync_site_content.py
pnpm install --frozen-lockfile
pnpm exec contentbit doctor --strict-seo
```

### Build lab sheets

```bash
python3 scripts/make_lab_pdf.py --all --strict
```

### Lint workflows

```bash
bash scripts/lint_workflows.sh
python3 scripts/validate_issue_forms.py
python3 scripts/test_ci_routing_matrix.py
```

## M0 exit checklist

| Issue | Title | Evidence |
|:---|:---|:---|
| [#64](https://github.com/duckurity/openlabs/issues/64) (M0-01) | Restore execution of the labs workflow | `.github/workflows/labs.yml` runs on pull requests; issue closed. |
| [#65](https://github.com/duckurity/openlabs/issues/65) (M0-02) | Establish the canonical lab catalog and two-status policy | `wiki/Lab-Catalog-Status.md`; `lab.yml` `status` field enforced in `validate.py`. |
| [#66](https://github.com/duckurity/openlabs/issues/66) (M0-03) | Prove the first supported reference lab through L0-L6 | `scripts/prove_reference_lab.py`; CI job **Prove duck-cross L0-L6**. |
| [#67](https://github.com/duckurity/openlabs/issues/67) (M0-04) | Make validation and CI aware of lab status | `scripts/lab_inventory.py`; `python3 scripts/test_validate_status.py`. |
| [#68](https://github.com/duckurity/openlabs/issues/68) (M0-05) | Triage every incomplete or invalid lab directory | `wiki/Lab-Triage-Inventory.md`; `scripts/lab_triage_inventory.py --check`. |
| [#69](https://github.com/duckurity/openlabs/issues/69) (M0-06) | Generate consistent catalog counts and listings | `scripts/sync_catalog_public.py --check`; public README catalog block. |
| [#70](https://github.com/duckurity/openlabs/issues/70) (M0-07) | Repair contributor issue intake | `scripts/validate_issue_forms.py`; `.github/ISSUE_TEMPLATE/`. |
| [#71](https://github.com/duckurity/openlabs/issues/71) (M0-08) | Make baseline CI efficient and safe to require | `wiki/Baseline-CI.md`; aggregate check **CI required**. |
| [#72](https://github.com/duckurity/openlabs/issues/72) (M0-09) | Publish baseline evidence and enable repository protections | `wiki/M0-Baseline-Evidence.md`; this report and manual protection record. |

## Branch protection (manual)

Configure in GitHub after [#71](https://github.com/duckurity/openlabs/issues/71) merge proves **CI required**. Record verification in [Branch protection record](Branch-Protection-Record).

### Required status checks

- **CI required** (`labs.yml`)
- **Lint workflows** (`workflow-lint.yml`) Pull requests that touch `.github/workflows/**` or workflow lint scripts.

### Recommended rules

- Require a pull request before merging: enabled for `main`
- Require status checks to pass: **CI required** always; **Lint workflows** when workflow files change
- Require branches to be up to date: enabled (recommended after first protected test PR passes)
- Allow force pushes: disabled on `main`
- Allow deletions: disabled on `main`

### Maintainer bypass policy

Organization or repository admins may bypass required checks only for documented emergencies. Record the reason, actor, and follow-up pull request in the M0 milestone completion comment.

### Verification record (fill manually)

| Field | Value |
|:---|:---|
| Verified by | _pending_ |
| Verified on | _pending_ |
| Settings export or screenshot | _pending_ |
| Protected-branch test PR | _pending_ |
| Notes | Fill after manual configuration. Do not enable required checks until M0-08 merge proves **CI required** on `main`. |
