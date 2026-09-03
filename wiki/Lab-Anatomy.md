## One lab, one directory

Every lab lives in its own directory after the template. The template lives
at `labs/_template/`. Validation skips the template and checks your copy.

```
labs/<track>/<lab>/
├── lab.yml              # name, track, difficulty, description, flag_hash
├── README.md            # player brief: story, setup, goal
├── docker-compose.yml   # service definition
├── Dockerfile           # pinned base image
└── app/                 # lab internals; the flag lives here
```

## `lab.yml`

Flat YAML, one `key: value` per line. Every field is required.

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

`README.md` is the player-facing brief. It has three parts.

1. **Title** with the difficulty and track.
2. **Brief**: the story and the surface.
3. **Goal**: how to check the solve.

The brief never contains the flag. It states the setup and the goal plainly.

## The service

`docker-compose.yml` defines one service with one documented host port.
`Dockerfile` pins a base image to a full version tag. `python:3.12-alpine`
is fine, `python:latest` is not. Prefer a digest pin when the base publishes
one.

## Where the flag lives

The plaintext flag appears only in files under the lab directory that ship
the service, inside `app/` and the like. It never appears in `lab.yml`, in
the lab `README.md`, or anywhere outside `labs/`.

## The validator

CI runs the same validator you run locally.

```bash
python3 scripts/validate.py
```

It checks structure, metadata, and flag hygiene. Add `--compose` to also run
`docker compose config` on every lab.

- `name` matches the directory
- `track` and `difficulty` are valid
- `flag_hash` is 64 lowercase hex
- no plaintext flag appears where it should not

A lab that passes validation is a lab that can merge.
