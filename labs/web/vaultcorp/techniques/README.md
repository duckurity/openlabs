# Technique pages (staged for openlabs)

These 4 files are drafts of the technique pages proposed for VaultCorp's
intake checklist (sub-issue #160). They follow the real
`content/technique/<slug>.mdx` frontmatter schema and body structure used
elsewhere in the `duckurity/openlabs` catalog (confirmed against existing
pages such as `idor.mdx`, `ssti.mdx`, and `mass-assignment.mdx`).

They are **staged here only** — not yet moved into `duckurity/openlabs` —
per the standing rule: nothing gets pushed to that repo until all 3
sub-issues are agreed with the maintainer. Once agreed, each file's final
home is:

```
content/technique/client-side-secret-leak-obfuscated-js.mdx
content/technique/ssrf-waf-bypass-ip-obfuscation.mdx
content/technique/hangfire-unauthenticated-dashboard-rce.mdx
content/technique/hidden-endpoint-directory-bruteforce.mdx
```

`lab.yml`'s `techniques:` field should be uncommented to list these 4 slugs
once the files land in `content/technique/` in openlabs (it currently keeps
them commented out, since the referenced files don't exist there yet and
the real `techniques: []` would otherwise fail validation that checks for
`content/technique/<slug>.mdx` existence).
