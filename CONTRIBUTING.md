# Contributing to openlabs

Read this before you open a pull request. It covers how labs are structured,
what CI checks, and the rules a lab must follow to be merged.

## Ways to contribute

- Author a lab
- Fix or improve an existing lab
- Improve documentation
- Report a broken lab through the issue forms

## Before you start

1. Read `README.md` for the structure and the voice this repository uses.
2. Copy `labs/_template/` into `labs/<track>/<lab-name>/`.
3. Fill in the metadata, write the brief, build the service, then run the
   validator:

   ```bash
   python3 scripts/validate.py
   ```

## Lab metadata

`lab.yml` is flat YAML, one `key: value` per line:

| Key | Rules |
|---|---|
| `name` | must match the directory name, lowercase, hyphens |
| `track` | one of `web`, `binary`, `crypto`, `network`, `osint` |
| `difficulty` | one of `easy`, `medium`, `hard`, `insane` |
| `description` | one line, shown in the lab index |
| `flag_hash` | SHA-256 of the full flag string, 64 lowercase hex |

Compute the hash from the exact flag string, braces included:

```bash
printf '%s' 'duck{your_flag_here}' | sha256sum
```

## Rules for labs

### Self-contained

The lab runs offline once images are pulled. No runtime calls to external
services, no license servers, no phone-home. Install dependencies at build
time only.

### Pinned images

Pin base images to a full version tag. `python:3.12-alpine` is acceptable;
`python:latest` is not. Prefer a digest pin when the base publishes one.

### Flags

- Format: `duck{...}`, matching `^duck\{[a-z0-9_]{16,40}\}$`
- Generate the body randomly. One flag per lab, never reused.
- Plaintext appears only inside lab internals, meaning service files under
  the lab directory. It never appears in `lab.yml`, in the lab `README.md`,
  or anywhere outside `labs/`.
- `flag_hash` is the only flag artifact the validator trusts.

### Ports

Expose one documented host port per lab. State it in the brief and in
`docker-compose.yml`. `8080` is the default; use alternatives only when the
lab needs them.

### Content

- Write the brief in this repository's voice: short declarative sentences,
  sentence-case headings, no exclamation marks, no larp phrasing.
- No real personal data. No third-party copyrighted content without
  permission.

## Difficulty rubric

Grade against what a player does, not how long it takes:

| Level | Expectation |
|---|---|
| `easy` | one clear vector, minimal recon, the brief points at the surface |
| `medium` | chained steps, some enumeration, the vector needs a decision |
| `hard` | multiple systems or stages, custom tooling, dead ends that punish assumptions |
| `insane` | research-level, an original technique, no public reference walkthrough |

Pick one tier. If a lab sits between two, grade down and let the solve rate
correct it later.

## Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description
```

Types: `feat`, `fix`, `docs`, `chore`, `ci`, `refactor`, `perf`, `test`,
`style`, `build`, `revert`. Example: `feat(web): add duck-cross lab`.

## Pull requests

1. One lab per pull request.
2. Run `python3 scripts/validate.py` locally; it must pass.
3. Use the pull request template checklist.
4. CI runs the same validator. All checks must pass before review.

Review covers structure, difficulty accuracy, voice, and whether the lab
runs from a clean clone.

## Licensing of contributions

By opening a pull request you agree your code is licensed under Apache-2.0
and your written content under CC-BY-4.0, as described in the README.
