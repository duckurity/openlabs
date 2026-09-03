# openlabs lab template

Copy this directory to `labs/<track>/<lab-name>/`, fill it in, then run
`python3 scripts/validate.py` from the repository root. CI skips this
template; it validates your copy.

- `lab.yml` — metadata. Replace every placeholder. `flag_hash` is
  `printf '%s' 'duck{...}' | sha256sum`.
- `README.md` — the player brief: story, setup, goal. No flag in here.
- `docker-compose.yml` — one service, one documented host port.
- `app/` — lab internals. The plaintext flag lives only in here.
