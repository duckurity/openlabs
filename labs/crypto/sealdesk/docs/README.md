# Maintainer documentation

**SealDesk · Documentation index · Updated 25 October 2026**

> **Audience:** Authors, maintainers, evaluators, and reviewers. These documents contain challenge spoilers. Give players only the [lab-root README](../README.md).

## Current status

SealDesk is an `experimental` crypto lab. The author-run playtest passed on 25 October 2026, and the author approved difficulty `medium`. An author-run playtest is not an independent playtest and does not provide independent difficulty calibration. Hosted CI and maintainer review remain pending. The validation report is the authoritative record of dated evidence, coverage limits, and release gates.

## Documentation set

| Document | Audience | Contents |
|---|---|---|
| [Challenge design](challenge-design.mdx) | Author, reviewer, evaluator | Learning objective, player journey, cryptographic contract, architecture, reset behavior, and difficulty decision |
| [Official solution](official-solution.mdx) | Evaluator | Spoiler-marked oracle observations, recovery method, document workflow, checker use, and evaluator automation |
| [Operations](operations.mdx) | Local operator | Prerequisites, exact startup and test commands, health checks, scoped reset, cleanup, troubleshooting, and runtime controls |
| [Remediation](remediation.mdx) | Developer | Root cause, secure verification order, defense in depth, regression matrix, and incident response |
| [Security report](security-report.mdx) | Security reviewer | Threat model, intentional finding, containment controls, negative tests, and accepted limitations |
| [Validation report](validation-report.mdx) | Release owner, maintainer, reviewer | Dated evidence ledger, coverage limits, reproduction commands, integration status, release gates, and the author-run playtest record |
| [This index](README.md) | Maintainer | Audience routing and publication boundaries |

## Reader and publication boundaries

- The root `README.md` is the player setup guide and challenge brief.
- The official solution and security report explain the intended padding-oracle behavior. Do not provide them during a player-only acceptance exercise.
- The application source, evaluator solver, operator helpers, Docker configuration, and these documents are maintainer and evaluator materials. The player's scope statement is not technical isolation for anyone with a repository checkout.
- Runtime flags, access codes, keys, flag digests, private evidence, machine-specific paths, and unredacted runtime output do not belong in this directory.

## Change control

Update the design contract when a route, cryptographic behavior, data boundary, flag lifecycle, topology, interface, or player-visible behavior changes. Update operations when commands, prerequisites, ports, or container controls change. Update remediation and security scope when the intentional flaw or its containment changes. Update the validation report only with evidence for the exact source revision. Keep test results, author approval, independent review, hosted CI, and maintainer review as separate claims.

After editing, check every local document link and heading anchor. Regenerate the challenge PDF only with the repository's canonical `scripts/make_lab_pdf.py` command. Keep private work material outside the challenge directory. Do not hand-edit shared OpenLabs fixtures, tests, registries, generators, workflows, or wiki sources for this lab.
