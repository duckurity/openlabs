<p align="center">
  <img src=".github/assets/banner.png?v=874ad199" alt="open labs" width="100%">
</p>

<p align="center">
  Open-source cybersecurity labs that run in Docker. Exploit a real service,
  find the flag, verify the solve. No accounts, no scoring server.
  A <a href="https://github.com/Duckurity">duckurity</a> project.
</p>

<p align="center">
  <a href="LICENSE"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/code-license-dark.svg?v=6164d6e0"><img src=".github/assets/badges/code-license-light.svg?v=d7baa62a" alt="code: Apache-2.0" height="20"></picture></a>
  <a href="LICENSE-CONTENT"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/content-license-dark.svg?v=b83304a6"><img src=".github/assets/badges/content-license-light.svg?v=b42ada1f" alt="content: CC-BY-4.0" height="20"></picture></a>
  <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/labs-count-dark.svg?v=5a5aee28"><img src=".github/assets/badges/labs-count-light.svg?v=91d62f45" alt="labs: 1 live" height="20"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/docker-dark.svg?v=2b6c885f"><img src=".github/assets/badges/docker-light.svg?v=d7abbc30" alt="docker: compose v2" height="20"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/checker-dark.svg?v=cff908fc"><img src=".github/assets/badges/checker-light.svg?v=6052eb0b" alt="checker: python3" height="20"></picture>
</p>

<p align="center">
  <a href="#get-solving">Quick start</a> · <a href="#labs-1-live">Labs</a> · <a href="https://github.com/Duckurity/openlabs/wiki">Wiki</a> · <a href="#contribute">Contribute</a>
</p>

## Listen

Press play to hear the welcome.

<audio controls src=".github/assets/audio/welcome.mp3?v=aa066c70">
  Your browser does not support the audio element.
</audio>

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

| Track | Examples |
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
| <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-easy-dark.svg?v=78286c0b"><img src=".github/assets/badges/chip-easy-light.svg?v=cb5cf439" alt="EASY" height="18"></picture> | one vector, minimal recon |
| <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-medium-dark.svg?v=f8ea61c4"><img src=".github/assets/badges/chip-medium-light.svg?v=60518fcc" alt="MEDIUM" height="18"></picture> | chained steps, some enumeration |
| <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-hard-dark.svg?v=1c4a365b"><img src=".github/assets/badges/chip-hard-light.svg?v=bcda98cd" alt="HARD" height="18"></picture> | multiple systems, custom tooling |
| <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-insane-dark.svg?v=02faac30"><img src=".github/assets/badges/chip-insane-light.svg?v=51dfad19" alt="INSANE" height="18"></picture> | research-level, an original technique |

</div>

## Labs <sub>1 live</sub>

<div align="center">

| Lab | Track | Difficulty | Description |
|:---:|:---:|:---:|:---|
| [`duck-cross`](labs/web/duck-cross) | `web` | <picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/badges/chip-easy-dark.svg?v=78286c0b"><img src=".github/assets/badges/chip-easy-light.svg?v=cb5cf439" alt="EASY" height="18"></picture> | a reports portal with a missing object-level authorization check |

</div>

## Flag format

<picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/mark-cross.svg?v=c2c360ee"><img src=".github/assets/mark-cross-light.svg?v=5db79627" alt="the openlabs mark" height="16" align="top"></picture> Every flag carries the mark: `duck{...}`. Lowercase letters, digits, and underscores between the braces, 16 to 40 characters.[^2]

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
      <source media="(prefers-color-scheme: dark)" srcset=".github/assets/powered-by.svg?v=f3ab6294">
      <img src=".github/assets/powered-by-light.svg?v=cda0d793" alt="powered by duckurity" width="110">
    </picture>
  </a>
</p>

[^1]: If port `8080` is taken on your machine, edit the host side of the
mapping in `docker-compose.yml`. The container port stays `8080`.

[^2]: `flag_hash` is the SHA-256 of the full flag string, braces included:
`printf '%s' 'duck{...}' | sha256sum`. Plaintext flags live only inside lab
internals.
