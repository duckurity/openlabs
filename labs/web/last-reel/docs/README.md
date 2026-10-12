# Maintainer documentation

**Last Reel · Documentation index · Updated 12 October 2026**

> **Audience:** Authors, maintainers, evaluators, and reviewers. These documents contain challenge spoilers. Give players only the [lab-root README](../README.md).

## Current status

This index describes the submitted Last Reel implementation. The validation report is the single source for test results, the release decision, and open repository items. Evidence from an earlier revision does not prove a later one.

## Documentation set

| Document | Audience | Contents |
|---|---|---|
| [Challenge design](challenge-design.mdx) | Author, reviewer, evaluator | Objective, player path, implementation contract, architecture, trust boundaries, reset and difficulty decisions |
| [Official solution](official-solution.mdx) | Evaluator | Spoiler-marked SQLi walkthrough, expected observations, checker use, evaluator automation |
| [Operations](operations.mdx) | Local operator | Prerequisites, first build, start, health, reset, logs, cleanup, isolation controls |
| [Remediation](remediation.mdx) | Developer | Root cause, parameterized repair, regression matrix, operational response |
| [Security report](security-report.mdx) | Security reviewer | Threat model, intentional finding, containment, tested negative cases, limitations |
| [Validation report](validation-report.mdx) | Release owner, maintainer, reviewer | Dated commands/results, coverage boundaries, integration blockers, acceptance gates |
| [This index](README.md) | Maintainer | Audience routing and publication boundaries |

## Reader and publication boundaries

- The root `README.md` is the only player setup and challenge brief.
- The official solution and security report disclose the intended search injection. Do not provide them before an unaided player acceptance exercise.
- The `docs/` directory, solver, application source, database source, reset helpers, and Docker configuration are maintainer/evaluator materials. None is served as an application route. This is an interface boundary, not a claim that a public source repository is secret.
- Runtime flags, credentials, private evidence, host-specific paths, and unredacted runtime output do not belong in this directory.
- The committed `lab.yml` contains a digest, not a plaintext flag. A local operator synchronization updates it for that disposable instance; do not publish a runtime flag or treat a locally synchronized digest as a release approval.

## Change control

Update the design contract when a route, query behavior, data boundary, flag lifecycle, topology, UI, or player-visible behavior changes. Update operations when commands, prerequisites, ports, or container controls change. Update remediation and security scope when the intentional flaw or its containment changes. Update the validation report only with evidence from the exact current source and distinguish a test result from independent acceptance or hosted CI.

After editing, check every local document link and heading anchor. Regenerate `last-reel.pdf` only with the repository's canonical `scripts/make_lab_pdf.py` command. Keep the challenge directory and its private workbench separate. Do not hand-edit shared OpenLabs fixtures, tests, registries, generators, workflows, or wiki sources for this lab.
