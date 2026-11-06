# Technique pages (staged for openlabs)

These 4 files are drafts of the technique pages proposed in `lab.yml` for
`nexawallet`'s intake checklist (sub-issue #161). They follow the real
`content/technique/<slug>.mdx` frontmatter schema and body structure used
elsewhere in the `duckurity/openlabs` catalog (same convention confirmed
earlier for VaultCorp's and dual-check's technique pages, against
`idor.mdx`, `ssti.mdx`, and `mass-assignment.mdx`).

Staged here only — not yet moved into `duckurity/openlabs` — per the
standing rule: nothing gets pushed to that repo until all 3 sub-issues
are agreed with the maintainer. Once agreed, each file's final home is:

```
content/technique/frida-framework-level-hooking-past-art-inlining.mdx
content/technique/non-exported-activity-is-not-an-access-boundary.mdx
content/technique/in-process-activity-launch-with-frida.mdx
content/technique/client-side-authorization-decisions.mdx
```

`lab.yml`'s `techniques:` field should be uncommented to list these 4
slugs once the files land in `content/technique/` in openlabs.
