## Purpose

Manual audit trail for [#72](https://github.com/duckurity/openlabs/issues/72)
(M0-09). GitHub branch protection is configured in the repository settings
UI. This page records who verified the settings and when.

Do not require **CI required** on `main` until
[#71](https://github.com/duckurity/openlabs/issues/71) is merged and a green
`main` run proves the aggregate check.

## Required status checks

| Check name | Workflow | When |
|:---|:---|:---|
| `CI required` | `labs.yml` | Every pull request that triggers the labs workflow |
| `Lint workflows` | `workflow-lint.yml` | Pull requests that change workflow or lint scripts |

See [Baseline CI](Baseline-CI) for routing and [M0 baseline evidence](M0-Baseline-Evidence)
for the full local command list.

## Recommended rules on `main`

| Setting | Value |
|:---|:---|
| Require a pull request before merging | enabled |
| Require status checks to pass | enabled |
| Require branches to be up to date before merging | enabled after first protected test PR |
| Allow force pushes | disabled |
| Allow deletions | disabled |

## Maintainer bypass policy

Organization or repository admins may bypass required checks only for
documented emergencies. Record the reason, actor, and follow-up pull request in
the M0 milestone completion comment on GitHub.

## Verification record

Fill this table after configuration. Attach a screenshot or exported rule
description in the milestone comment.

| Field | Value |
|:---|:---|
| Verified by | _pending_ |
| Verified on | _pending_ |
| Settings export or screenshot URL | _pending_ |
| Protected-branch test PR | _pending_ |
| Notes | Enable checks only after **CI required** is green on `main`. |

Machine-readable defaults live in
`scripts/fixtures/m0_branch_protection.json`.
