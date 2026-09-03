## What changes

<!-- One lab per pull request. State the lab path if you add or change one. -->

## Checklist

- [ ] `python3 scripts/validate.py` passes locally
- [ ] The lab starts from a clean clone with `docker compose up -d`
- [ ] The flag matches `^duck\{[a-z0-9_]{16,40}\}$` and `flag_hash` matches `printf '%s' '<flag>' | sha256sum`
- [ ] No plaintext flag in `lab.yml`, in the lab `README.md`, or outside the lab directory
- [ ] Base images pinned to full version tags, no runtime network dependencies
- [ ] One documented host port, stated in the brief
- [ ] Conventional commit title (`type(scope): description`)
