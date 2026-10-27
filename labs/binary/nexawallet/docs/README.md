# Maintainer + player docs (staged for openlabs)

Per the maintainer's review on sub-issue #161 ("align paths to
`docs/*.mdx`, not `documentation/`"), everything for this lab now lives
under this one `docs/` folder — the original narrative write-ups that
used to live under a separate `documentation/` folder have been folded
into the files below, and that folder has been removed:

- `README.md` (this file)
- `player-briefing.mdx` — player-facing, no-spoiler description (was
  `documentation/Public Briefing.md`)
- `challenge-design.mdx` — catalog-facing design summary; now also
  includes the "Skills exercised" / "What is explicitly not being
  tested" sections (was `documentation/Objective.md`)
- `official-solution.mdx` — maintainer/evaluator spoiler solution; now
  also includes the full narrated, screenshot-illustrated walkthrough
  (was `documentation/Walkthrough.md`), with its screenshots moved to
  `images/`
- `operations.mdx`
- `remediation.mdx` — now cross-references the root-cause analysis in
  `security-report.mdx` instead of a separate file (was
  `documentation/Mitigation.md`, mapped onto findings previously in
  `documentation/What Happened and Why (Root Cause).md`)
- `security-report.mdx` — now includes a full "Root cause analysis"
  section (was `documentation/What Happened and Why (Root Cause).md`)
- `validation-report.mdx`
- `images/` — screenshots referenced from `official-solution.mdx`

This satisfies sub-issue #161's "seven-document pattern where
applicable" checklist item (the original seven maintainer files are all
still present, scaled to a BYOD artifact-only mobile lab with no
server-side component, matching `labs/web/firmdrama/docs/`'s naming
convention), plus the two additions (`player-briefing.mdx`, `images/`)
needed to consolidate the previously-separate narrative documentation
into this single tree.

`labs/binary/` doesn't exist yet anywhere in `duckurity/openlabs` as of
this writing — `dual-check` (sub-issue #162) and this lab are expected to
be among the catalog's first binary-track labs, each landing in its own
PR per the maintainer's note on issue #161.

Staged here only, per the standing rule: nothing gets pushed to
`duckurity/openlabs` until all 3 sub-issues are agreed with the
maintainer. Final home once agreed:

```
labs/binary/nexawallet/docs/README.md
labs/binary/nexawallet/docs/player-briefing.mdx
labs/binary/nexawallet/docs/challenge-design.mdx
labs/binary/nexawallet/docs/official-solution.mdx
labs/binary/nexawallet/docs/operations.mdx
labs/binary/nexawallet/docs/remediation.mdx
labs/binary/nexawallet/docs/security-report.mdx
labs/binary/nexawallet/docs/validation-report.mdx
labs/binary/nexawallet/docs/images/
```

See `validation-report.mdx` for what is and isn't verified yet.
