# Security policy

## What needs a report

openlabs ships services that are vulnerable by design. A vulnerability inside
a lab that the brief points at is the product. It needs no report.

Report a vulnerability when it affects:

- Lab infrastructure outside the intended scope: a container that can reach
  the host, a bind mount that exposes host files, a privileged or host-network
  service the brief does not declare
- Repository tooling: `scripts/validate.py`, `scripts/check.py`, CI workflows
- The repository itself: an unintended way to leak another lab's flag hash
  preimage or to inject content into validated metadata

## How to report

Use [GitHub Private Vulnerability Reporting](https://github.com/duckurity/openlabs/security/advisories/new).

Do not report vulnerabilities through public GitHub issues.

Include:

- What is affected and where (path or workflow)
- Steps to reproduce
- Impact as you understand it

## What happens next

Maintainers acknowledge a report within 7 days and publish a fix or a
mitigation within 90 days. Reporters who ask for credit receive it in the
fix commit and the release notes.

## Supported versions

| Version | Supported |
|---|---|
| latest | Yes |
| < latest | No |
