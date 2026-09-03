This guide is for content writers. It covers the voice, the structure, and
the rules a lab needs to merge. If you have not read
[Lab Anatomy](Lab-Anatomy) and [Flag Format](Flag-Format), start there.

## One lab, one pull request

1. Copy `labs/_template/` into `labs/<track>/<lab-name>/`.
2. Fill in the metadata.
3. Write the brief.
4. Build the service.
5. Run the validator.
6. Open a pull request.

CI runs the same validator. All checks must pass before review.

## The voice

Written content follows one voice. Short declaratives. One idea per
sentence. Sentence-case headings. No exclamation marks, no em-dashes, no
superlatives, no adverbs, no hype, no larp.

Terms that mean specific things:

| Term | Meaning |
|---|---|
| `lab` | one service, one brief, one flag |
| `flag` | the `duck{...}` value |
| `solve` | the act and the result of finding the flag |
| `writeup` | a player's published explanation of a solve |

Difficulty, lowercase in prose, uppercase only in mono badges:
`easy`, `medium`, `hard`, `insane`.

Put values in code spans: ports, commands, formats. This keeps prose clean
and makes the concrete things scannable.

### Rewrite, do not decorate

| Avoid | Prefer |
|---|---|
| "This lab will teach you a lot" | "Find the flag in the restricted report." |
| "Never underestimate the power of IDOR" | "The portal checks ownership on one route." |
| "Wow, what a challenge!" | "Wardens file crossing reports. One is restricted." |

The brief points at the surface. It does not hand over the solve.

## Metadata

`lab.yml` is flat YAML. Every field required.

<div align="center">

| Key | Rules |
|:---:|:---|
| `name` | matches the directory name, lowercase, hyphens |
| `track` | one of `web`, `binary`, `crypto`, `network`, `osint` |
| `difficulty` | one of `easy`, `medium`, `hard`, `insane` |
| `description` | one line, shown in the lab index |
| `flag_hash` | SHA-256 of the full flag string, 64 lowercase hex |

</div>

## The brief

`README.md` has three parts.

1. **Title**: the lab name, `EASY` · `web`.
2. **Brief**: the story and the surface. Set up the world in two or three
   sentences. Name who is involved and what is at stake.
3. **Setup** and **Goal**: exact commands to run, the URL to open, and how
   to check the solve.

Write the goal as an instruction, not a hint. "Find the restricted report
and its flag" states the target without giving the path.

## Difficulty, graded on action

Grade against what a player does, not how long it takes. See
[Tracks and Difficulty](Tracks-and-Difficulty) for the rubric. If a lab sits
between two tiers, grade down.

## Flags

- Format `duck{...}`, matching `^duck\{[a-z0-9_]{16,40}\}$`.
- Generate the body randomly. One flag per lab, never reused.
- The plaintext appears only in lab internals, the service files under the
  lab directory. Never in `lab.yml`, never in the brief, never outside
  `labs/`.
- Compute the hash from the exact flag string, braces included:

  ```bash
  printf '%s' 'duck{your_flag_here}' | sha256sum
  ```

## Self-contained services

- The lab runs offline once images are pulled.
- No runtime calls to external services, no license servers, no phone-home.
- Install dependencies at build time only.

## Pinned images

Pin base images to a full version tag. `python:3.12-alpine` is acceptable,
`python:latest` is not. Prefer a digest pin when the base publishes one.

## Ports

Expose one documented host port per lab. State it in the brief and in
`docker-compose.yml`. `8080` is the default. Use alternatives only when the
lab needs them.

## Real data and content

- No real personal data.
- No third-party copyrighted content without permission.
- A vulnerable service is the point. It is not a reportable weakness.

## Before you submit

```bash
python3 scripts/validate.py
python3 scripts/validate.py --compose
```

Both must pass from a clean clone. Then open the pull request and meet
every item on the [Reviewer Checklist](Reviewer-Checklist).
