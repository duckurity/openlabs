<p align="center">
  <img src=".github/assets/banner.png" alt="open labs" width="100%">
</p>

<p align="center">
  Open-source cybersecurity labs that run in Docker. Exploit a real service,
  find the flag, verify the solve. No accounts, no scoring server.
  A <a href="https://github.com/Duckurity">duckurity</a> project.
</p>

<p align="center">
  <a href="LICENSE"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/code-license-dark.svg"><img src=".github/assets/badges/code-license-light.svg" alt="code: Apache-2.0" height="20"></picture></a>
  <a href="LICENSE-CONTENT"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/content-license-dark.svg"><img src=".github/assets/badges/content-license-light.svg" alt="content: CC-BY-4.0" height="20"></picture></a>
  <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/labs-count-dark.svg"><img src=".github/assets/badges/labs-count-light.svg" alt="labs: 1 live" height="20"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/docker-dark.svg"><img src=".github/assets/badges/docker-light.svg" alt="docker: compose v2" height="20"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/checker-dark.svg"><img src=".github/assets/badges/checker-light.svg" alt="checker: python3" height="20"></picture>
</p>

<p align="center">
  <a href="#get-solving">Quick start</a> · <a href="#labs-1-live">Labs</a> · <a href="https://github.com/Duckurity/openlabs/wiki">Wiki</a> · <a href="#contribute">Contribute</a>
</p>

## Get solving

Three things stand between you and your first flag.

```bash
git clone https://github.com/Duckurity/openlabs
cd openlabs/labs/web/duck-cross
docker compose up -d
```

Open `http://localhost:8080`, work the brief until the flag turns up, then
check the solve:

```bash
python3 scripts/check.py labs/web/duck-cross
```

The checker hashes your input with SHA-256 and compares it against
`flag_hash` in `lab.yml`. It prints `solved` or `not solved`.[^1]

> [!TIP]
> After images are pulled, nothing leaves your machine. Labs are
> self-contained and fully offline.

Every lab is a self-contained exercise: one vulnerable service, one brief,
one flag inside. You solve at your own pace, and honesty is built in. The
repository stores only the SHA-256 hash of each flag, never the plaintext.

## What makes a lab

<div align="center">

| | |
|:---|:---|
| **Self-contained** | Runs offline once images are pulled. No phone-home. |
| **Reproducible** | Pinned base images, one documented host port. |
| **Honest** | Plaintext flags stay inside lab internals; only the hash ships. |
| **Graded** | A four-step difficulty ladder from `easy` to `insane`. |

</div>

## Tracks

<div align="center">

| Track | Focus |
|:---:|:---|
| `web` | injection, broken access control, auth bypass, SSRF |
| `binary` | memory corruption, exploitation, reverse engineering |
| `crypto` | weak primitives, protocol misuse, implementation faults |
| `network` | protocol abuse, traffic analysis, pivoting |
| `osint` | recon, source analysis, signature tracing |

</div>

## Difficulty

`easy` → `medium` → `hard` → `insane`. Grades describe what a player does,
not how long it takes.

<div align="center">

| Level | Expectation |
|:---:|:---|
| <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-easy-dark.svg"><img src=".github/assets/badges/chip-easy-light.svg" alt="EASY" height="18"></picture> | one vector, minimal recon |
| <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-medium-dark.svg"><img src=".github/assets/badges/chip-medium-light.svg" alt="MEDIUM" height="18"></picture> | chained steps, some enumeration |
| <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-hard-dark.svg"><img src=".github/assets/badges/chip-hard-light.svg" alt="HARD" height="18"></picture> | multiple systems, custom tooling |
| <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-insane-dark.svg"><img src=".github/assets/badges/chip-insane-light.svg" alt="INSANE" height="18"></picture> | research-level, an original technique |

</div>

## Labs <sub>1 live</sub>

<div align="center">

| Lab | Track | Difficulty | Description |
|:---:|:---:|:---:|:---|
| [`duck-cross`](labs/web/duck-cross) | `web` | <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-easy-dark.svg"><img src=".github/assets/badges/chip-easy-light.svg" alt="EASY" height="18"></picture> | a reports portal with a missing object-level authorization check |

</div>

## Flag format

<picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/mark-cross.svg"><img src=".github/assets/mark-cross-light.svg" alt="the openlabs mark" height="16" align="top"></picture> Every flag carries the mark: `duck{...}`. Lowercase letters, digits, and underscores between the braces, 16 to 40 characters.[^2]

The plaintext flag lives inside the lab; the repository stores only its
SHA-256 hash. Reading lab source to find the flag is a legitimate solve.
Open labs work that way.

## Anatomy of a lab

```
labs/<track>/<lab>/
├── lab.yml              # name, track, difficulty, description, flag_hash
├── README.md            # player brief: story, setup, goal
├── docker-compose.yml   # service definition
├── Dockerfile           # pinned base image
└── app/                 # lab internals; the flag lives here
```

`labs/_template/` carries the skeleton. Copy it, fill it in, and open a
pull request. CI validates structure, metadata, and flag hygiene on every
change.

## Writeups

A writeup is your own explanation of a solve. Publish them anywhere. Link
the lab so other people can follow the path you took.

## Contribute

Labs are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a
pull request. For behavior standards, see
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The full player and authoring
guides live on the [project wiki](https://github.com/Duckurity/openlabs/wiki).

<details>
<summary><samp>How a lab ships</samp></summary>

```mermaid
flowchart LR
    idea["Lab idea<br>issue form"] --> author["Copy<br>labs/_template"]
    author --> pr["Pull request"]
    pr --> ci{"CI validates"}
    ci -->|"fix"| author
    ci -->|"pass"| review["Review"]
    review --> ship["Merged into<br>labs/"]
```

</details>

## Licensing

Code, configuration, and scripts fall under [Apache-2.0](LICENSE). Lab
briefs, docs, and prose fall under [CC-BY-4.0](LICENSE-CONTENT). One
repository, two licenses.

## Security

The vulnerabilities inside labs are the product; they need no report.
Weaknesses in lab infrastructure, repo tooling, or CI go through
[GitHub Private Vulnerability Reporting](https://github.com/Duckurity/openlabs/security/advisories/new).
Details in [SECURITY.md](SECURITY.md).

<p align="center">
  <a href="https://github.com/Duckurity">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/assets/powered-by.svg">
      <img src=".github/assets/powered-by-light.svg" alt="powered by duckurity" width="110">
    </picture>
  </a>
</p>

[^1]: If port `8080` is taken on your machine, edit the host side of the
mapping in `docker-compose.yml`. The container port stays `8080`.

[^2]: `flag_hash` is the SHA-256 of the full flag string, braces included:
`printf '%s' 'duck{...}' | sha256sum`. Plaintext flags live only inside lab
internals.
