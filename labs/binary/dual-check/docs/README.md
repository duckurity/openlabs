# Maintainer + player docs (staged for openlabs)

All narrative and maintainer documentation for this lab now lives under
this one `docs/` folder — the original narrative write-ups that used to
live under a separate `documentation/` folder have been folded into the
files below, and that folder has been removed:

- `README.md` (this file)
- `player-briefing.mdx` — player-facing, no-spoiler description (was
  `documentation/Public Briefing ....md`)
- `challenge-design.mdx` — catalog-facing design summary; now also
  includes a "Skills exercised" section (was `documentation/Objective
  ....md`)
- `official-solution.mdx` — maintainer/evaluator spoiler solution; now
  also includes the full narrated, screenshot-illustrated walkthrough
  (was `documentation/Walkthrough ....md`), with its screenshots moved
  to `images/`. Includes a provenance note on the screenshot run's flag
  value, which predates the current `lab.yml` `flag_hash` (see
  `validation-report.mdx` for the format-compliance fix).
- `security-report.mdx` — new; the root-cause / "why this is realistic"
  writeup (was `documentation/What Happened and Why (Root Cause)
  ....md`)
- `remediation.mdx` — new; detailed fixes for real client-side systems
  (was `documentation/Mitigation ....md`)
- `validation-report.mdx`
- `images/` — screenshots referenced from `official-solution.mdx`

This satisfies sub-issue #162's "maintainer docs" checklist item and
M9nx's follow-up request to move maintainer docs under `docs/`, plus adds
`security-report.mdx` and `remediation.mdx` (previously omitted since
this lab has no running service) for experimental parity with the
catalog's other two labs from this submission.

Note: `labs/binary/` doesn't exist yet anywhere in `duckurity/openlabs` —
this will be the catalog's first binary-track lab, confirmed by checking
the live repository before writing these docs.

Staged here only, per the standing rule: nothing gets pushed to
`duckurity/openlabs` until all 3 sub-issues are agreed with the
maintainer. Final home once agreed:

```
labs/binary/dual-check/docs/README.md
labs/binary/dual-check/docs/player-briefing.mdx
labs/binary/dual-check/docs/challenge-design.mdx
labs/binary/dual-check/docs/official-solution.mdx
labs/binary/dual-check/docs/security-report.mdx
labs/binary/dual-check/docs/remediation.mdx
labs/binary/dual-check/docs/validation-report.mdx
labs/binary/dual-check/docs/images/
```
