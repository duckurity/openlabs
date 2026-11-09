# How to Fix or Mitigate

- Use parameterized queries so search input is treated only as data.
- Allowlist any selectable search fields or modes.
- Keep internal records out of ordinary search results and enforce access checks where data is read.
- Give the database account only the permissions it needs.
- Add tests to confirm that search input cannot expose internal records.
