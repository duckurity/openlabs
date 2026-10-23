## Purpose

Document the baseline labs workflow (`labs.yml`) for maintainers and branch
protection. Issue [#71](https://github.com/duckurity/openlabs/issues/71)
(M0-08) defines the policy this page summarizes.

## Required check name

Configure branch protection on:

| Check name | Workflow job |
|:---|:---|
| `CI required` | `ci-required` in `labs.yml` |

Do not require matrix-generated names or skipped jobs individually. The
aggregate job fails when any in-scope job fails and passes when out-of-scope
jobs are skipped.

Workflow changes should also require **`Lint workflows`** from
`workflow-lint.yml`.

## Concurrency

Pull requests use `cancel-in-progress` on the labs workflow group so superseded
pushes stop expensive work.

## When the full baseline runs

`push` to `main` and `workflow_dispatch` always run every labs job.

Pull requests always start the **labs** workflow and run **Detect change scope**
first. Path filters in that job mark which expensive jobs run; **CI required**
still reports on every pull request.

**Dependabot pull requests** always run the full baseline (same jobs as `push`
to `main`). Root `package.json` / lockfile bumps only matched the content
scope before M0-08 follow-up, which skipped **Validate labs** (including the
M0 wiki check) on the PR but ran it on merge to `main`.

## Change-to-job matrix

| Change example | Validate | Security | Content | PDF | duck-cross proof |
|:---|:---:|:---:|:---:|:---:|:---:|
| Dependabot: root `package.json` only | yes | yes | yes | yes | yes |
| `scripts/validate_issue_forms.py` only | yes | no | no | no | no |
| `templates/labsheet.cls` only | no | no | no | yes | no |
| `content/**/*.mdx` only | no | no | yes | no | no |
| `labs/web/duck-cross/**` | yes | yes | no* | yes | yes |

\* Content runs when the diff also touches `content/**`, site sync scripts, or
root `package.json` / lockfile paths in the content filter.
| `wiki/**` only | no | no | no | no | no |

Machine-readable examples live in
`scripts/fixtures/ci_routing_matrix.json`. Verify with
`python3 scripts/test_ci_routing_matrix.py`.

## Permissions

Labs jobs on pull requests use `contents: read` only. No workflow grants write
permissions or exposes secrets to untrusted fork code beyond what GitHub
provides to Actions on PRs.

## Evidence commands

```bash
python3 scripts/test_m2.py
python3 scripts/test_ci_routing_matrix.py
bash scripts/lint_workflows.sh
python3 scripts/baseline_report.py --check --wiki wiki/M0-Baseline-Evidence.md
```

The **Prove duck-cross L0-L6** job uploads legacy prove evidence and a Tier 1
`openlabs` lifecycle JSON. Both artifacts are redacted and size-bounded before
upload.

For the full M0 completion record and local equivalents to every CI job, see
[M0 baseline evidence](M0-Baseline-Evidence) ([#72](https://github.com/duckurity/openlabs/issues/72)).
Branch protection verification is manual; use [Branch protection record](Branch-Protection-Record).

After merge, compare Actions minutes across five representative pull requests
(docs-only outside labs, tooling-only, single-lab, content, workflow).
