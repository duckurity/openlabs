# M1-06 open lab pull request migration

After [M1-06](https://github.com/duckurity/openlabs/issues/109) and the
[M1-09 v1 freeze](M1-09-Contract-v1-Freeze) on `main`, every catalogued
`lab.yml` and `labs/_template/lab.yml` declares `contract_version: 1`.
Open lab branches that touch metadata must rebase and align before merge.

## What to add

At the top of `lab.yml`:

```yaml
contract_version: 1
```

Keep existing `name`, `track`, `difficulty`, `description`, `flag_hash`, `status`,
and `techniques` values unchanged unless you are fixing a separate metadata bug.
Do not change `status` as part of this migration.

## Branches to rebase

| Pull request | Action |
|:---|:---|
| [#58](https://github.com/duckurity/openlabs/pull/58) | Add `contract_version: 1` when the lab is catalogued |
| [#57](https://github.com/duckurity/openlabs/pull/57) | Rebase on `main`; add `contract_version: 1` if `lab.yml` diverges |
| Dependabot lab PRs | Rebase after M1-06 if they modify `lab.yml` |

Uncatalogued directories under `labs/` without `lab.yml` are unchanged.

## Verify locally

```bash
python3 scripts/validate.py
python3 scripts/test_contract.py
python3 scripts/sync_catalog_public.py --check
OPENLABS_SYNC_HERMETIC=1 python3 scripts/sync_site_content.py --check
```

## Rollback

Revert the M1-06 merge commit. Lab services and flags are unchanged; only metadata
headers and any regenerated catalog or site output from that commit revert.
