# Maintainer + player docs (staged for openlabs)

All narrative and maintainer documentation for this lab now lives under
this one `docs/` folder — the original narrative write-ups that used to
live under a separate `documentation/` folder have been folded into the
files below, and that folder has been removed:

- `README.md` (this file)
- `player-briefing.mdx` — player-facing, no-spoiler description (was
  `documentation/Public Briefing.md`)
- `challenge-design.mdx` — catalog-facing design summary; now also
  includes the "Skills exercised" stage table (was
  `documentation/Objective.md`)
- `official-solution.mdx` — maintainer/evaluator spoiler solution; now
  also includes the full narrated, screenshot-illustrated walkthrough
  (was `documentation/Walkthrough.md`), with its screenshots moved to
  `images/`
- `operations.mdx`
- `security-report.mdx` — already included the full root-cause
  vulnerability writeup (`documentation/What Happened and Why (Root
  Cause).md`'s content was a less detailed duplicate of this)
- `remediation.mdx` — detailed fixes with code examples (was
  `documentation/Mitigation.md`)
- `validation-report.mdx`
- `images/` — screenshots referenced from `official-solution.mdx`

This satisfies sub-issue #160's "maintainer docs" checklist item,
following the convention found in `labs/web/firmdrama/docs/`, plus the
two additions (`player-briefing.mdx`, `images/`) needed to consolidate
the previously-separate narrative documentation into this single tree.

Staged here only, per the standing rule: nothing gets pushed to
`duckurity/openlabs` until all 3 sub-issues are agreed with the
maintainer. Final home once agreed:

```
labs/web/vaultcorp-ssrf-rce/docs/README.md
labs/web/vaultcorp-ssrf-rce/docs/player-briefing.mdx
labs/web/vaultcorp-ssrf-rce/docs/challenge-design.mdx
labs/web/vaultcorp-ssrf-rce/docs/official-solution.mdx
labs/web/vaultcorp-ssrf-rce/docs/operations.mdx
labs/web/vaultcorp-ssrf-rce/docs/security-report.mdx
labs/web/vaultcorp-ssrf-rce/docs/remediation.mdx
labs/web/vaultcorp-ssrf-rce/docs/validation-report.mdx
labs/web/vaultcorp-ssrf-rce/docs/images/
```
