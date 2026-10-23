# Contributing to openlabs

Read this before you open a pull request. It covers how labs are structured,
what CI checks, and the rules a lab must follow to be merged.

## Ways to contribute

- Author a lab
- Fix or improve an existing lab
- Improve documentation
- Report a broken lab through the [lab bug issue form](https://github.com/duckurity/openlabs/issues/new?template=lab-bug.yml)

See [SUPPORT.md](SUPPORT.md) for other intake paths. Do not use public issues
for security reports; use [private vulnerability reporting](https://github.com/duckurity/openlabs/security/advisories/new).

## Before you start

1. Read `README.md` for the structure and the voice this repository uses.
2. Copy `labs/_template/` into `labs/<track>/<lab-name>/`.
3. Fill in the metadata, write the brief, build the service, then run the
   validator:

   ```bash
   python3 scripts/validate.py
   python3 scripts/test_contract.py
   ```

## Contract conformance

Lab metadata uses **contract v1** (`contract_version: 1`). Machine-readable
definitions live under `contracts/`. Run the CI gate locally:

```bash
python3 scripts/test_contract.py
```

Validator output may include `OL-####` ids from `contracts/diagnostics.json`.
Look up the id or symbolic key in that file. Diagnostic text is redacted for
flags, secrets, and home paths before it appears in logs.

The `openlabs` CLI in `contracts/cli-v1.md` is a specification only. The
repository does not ship that command yet. Use `scripts/validate.py` and
`scripts/check.py` instead.

## Lab metadata

`lab.yml` is flat YAML, one `key: value` per line:

| Key | Rules |
|---|---|
| `contract_version` | integer `1` (required on `main` after M1-06) |
| `name` | must match the directory name, lowercase, hyphens |
| `track` | one of `web`, `binary`, `crypto`, `network`, `osint` |
| `difficulty` | one of `easy`, `medium`, `hard`, `insane` |
| `description` | one line, shown in the lab index |
| `flag_hash` | SHA-256 of the full flag string, 64 lowercase hex |
| `status` | `experimental` or `supported` |
| `techniques` | bracket list of technique slugs, or `[]`; each slug needs `content/technique/<slug>.mdx` |
| `checkpoint_flag_hash` | optional; same 64 lowercase hex pattern as `flag_hash` |
| `port` | optional integer `1`–`65535`; site sync usually derives port from README or compose |

Unknown top-level keys are rejected. Match `contracts/lab.schema.json` and
`wiki/M1-Contract-Decisions.md`.

See [M1-09 contract v1 freeze](wiki/M1-09-Contract-v1-Freeze.md) and
[M1-06 open lab PR migration](wiki/M1-06-Open-Lab-PR-Migration.md) if your branch
predates `contract_version: 1` on `main`.

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

## Workflow files

When you change files under `.github/workflows/`, run:

```bash
bash scripts/lint_workflows.sh
```

Install `actionlint` v1.7.7 from
https://github.com/rhysd/actionlint/releases/tag/v1.7.7 and verify the
linux_amd64 tarball against `actionlint_1.7.7_checksums.txt` from the same
release. The script does not download or install tools for you.

## Pull requests

1. One lab per pull request.
2. Run `python3 scripts/validate.py` and `python3 scripts/test_contract.py` locally; both must pass.
3. Use the pull request template checklist.
4. CI runs the same validator. All checks must pass before review.

Review covers structure, difficulty accuracy, voice, and whether the lab
runs from a clean clone.

## Licensing of contributions

By opening a pull request you agree your code is licensed under Apache-2.0
and your written content under CC-BY-4.0, as described in the README.
