## Purpose

Parent triage for [#68](https://github.com/duckurity/openlabs/issues/68) (M0-05). Every directory under `labs/<track>/` has a recorded decision. Repairs happen in separate issues and pull requests. Do not infer `supported` from a score of 70 or higher.

Reviewed on `2026-09-26`. Regenerate with `python3 scripts/lab_triage_inventory.py --write-wiki wiki/Lab-Triage-Inventory.md`.

## Evidence commands

```bash
python3 scripts/lab_triage_inventory.py --json triage-evidence.json
python3 scripts/validate.py --json validate-report.json
python3 scripts/score_lab.py --min 70 --json score-report.json
```

## Summary

- Directories inventoried: **25** (issue #68 opened at 24; `duckexchange` added after that count).
- Catalogued: **20**; uncatalogued: **5**.
- Score gate reference: **70** (recommendations only).

## Inventory

| Directory | Catalog status | Score | Structural blockers | Score recommendations | Action | Owner | Follow-up issue title |
|:---|:---:|:---:|:---|:---|:---|:---|:---|
| `labs/web/Sayed_Khashana_REST_API_IDOR_CTF` | uncatalogued | 60 | directory name 'Sayed_Khashana_REST_API_IDOR_CTF' fails NAME_RE | score 60 is below threshold 70; structure: missing lab.yml; docs: README missing ## Brief; docs: README missing ## Setup; docs: README missing ## Goal | keep_uncatalogued | maintainers | M0-05 follow-up: rename and catalog Sayed Khashana REST IDOR lab |
| `labs/web/aegis-ctf` | experimental | 100 | none | none | maintain | maintainers | none |
| `labs/web/cafe-house-rules` | experimental | 91 | none | dockerfile: no USER directive (runs as root); docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/cloudvault` | experimental | 100 | none | none | maintain | maintainers | none |
| `labs/web/duck-cross` | supported | 97 | none | docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/duck-nest` | experimental | 97 | none | docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/duckcorp-savegame` | uncatalogued | 39 | missing compose file | score 39 is below threshold 70; structure: missing docker-compose.yml (or compose.yml); structure: missing lab.yml; dockerfile: no USER directive (runs as root); compose: missing compose file | keep_uncatalogued | maintainers | M0-05 follow-up: compose and lab.yml for duckcorp-savegame or approved removal |
| `labs/web/duckdesk` | uncatalogued | 50 | none | score 50 is below threshold 70; structure: missing lab.yml; dockerfile: no USER directive (runs as root); compose: no explicit restart policy; docs: README missing ## Brief | keep_uncatalogued | maintainers | M0-05 follow-up: catalog duckdesk as experimental |
| `labs/web/duckexchange` | experimental | 100 | none | none | catalog_experimental_review | maintainers | M0-05 follow-up: L0-L6 review for duckexchange promotion |
| `labs/web/duckfleet` | uncatalogued | 50 | none | score 50 is below threshold 70; structure: missing lab.yml; dockerfile: no USER directive (runs as root); compose: no explicit restart policy; docs: README missing ## Brief | keep_uncatalogued | maintainers | M0-05 follow-up: catalog duckfleet as experimental |
| `labs/web/duckmarket` | uncatalogued | 60 | none | score 60 is below threshold 70; structure: missing lab.yml; docs: README missing ## Brief; docs: README missing ## Setup; docs: README missing ## Goal | keep_uncatalogued | maintainers | M0-05 follow-up: catalog duckmarket as experimental |
| `labs/web/duckrpc-archive` | experimental | 100 | none | none | maintain | maintainers | none |
| `labs/web/duckvault` | experimental | 92 | none | compose: host port not stated in the brief; docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/duckvault-web-ctf` | experimental | 100 | none | none | maintain | maintainers | none |
| `labs/web/fieldops-360` | experimental | 97 | none | docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/firmdrama` | experimental | 100 | none | none | maintain | maintainers | none |
| `labs/web/invoiceportal` | experimental | 78 | none | dockerfile: no USER directive (runs as root); docs: README missing ## Goal; docs: no challenge-sheet PDF beside the lab | maintain | maintainers | M0-05 follow-up: raise invoiceportal score hygiene (optional) |
| `labs/web/nexora-platform` | experimental | 97 | none | docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/shopvault` | experimental | 97 | none | docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/snapconnect` | experimental | 81 | none | dockerfile: no USER directive (runs as root); docs: no challenge-sheet PDF beside the lab | maintain | maintainers | M0-05 follow-up: snapconnect techniques and docs score pass |
| `labs/web/snapsync` | experimental | 81 | none | dockerfile: no USER directive (runs as root); docs: no challenge-sheet PDF beside the lab | maintain | maintainers | M0-05 follow-up: snapsync techniques and Dockerfile score pass |
| `labs/web/switf01-hit3` | experimental | 77 | none | docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/techvault` | experimental | 97 | none | docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/threadline` | experimental | 97 | none | docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |
| `labs/web/vault-api` | experimental | 92 | none | compose: host port not stated in the brief; docs: no challenge-sheet PDF beside the lab | maintain | maintainers | none |

## Follow-up issues to file

Open one GitHub issue per title below. Link the issue back to #68. Do not batch unrelated labs in one remediation pull request.

- M0-05 follow-up: rename and catalog Sayed Khashana REST IDOR lab
- M0-05 follow-up: compose and lab.yml for duckcorp-savegame or approved removal
- M0-05 follow-up: catalog duckdesk as experimental
- M0-05 follow-up: L0-L6 review for duckexchange promotion
- M0-05 follow-up: catalog duckfleet as experimental
- M0-05 follow-up: catalog duckmarket as experimental
- M0-05 follow-up: raise invoiceportal score hygiene (optional)
- M0-05 follow-up: snapconnect techniques and docs score pass
- M0-05 follow-up: snapsync techniques and Dockerfile score pass
