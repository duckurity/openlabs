<p align="center">
  <img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/banner.png?v=874ad199" alt="open labs" width="100%">
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/code-license-dark.svg?v=6164d6e0">
    <img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/code-license-light.svg?v=d7baa62a" alt="code: Apache-2.0" height="20">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/content-license-dark.svg?v=b83304a6">
    <img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/content-license-light.svg?v=b42ada1f" alt="content: CC-BY-4.0" height="20">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/labs-count-dark.svg?v=5a5aee28">
    <img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/labs-count-light.svg?v=91d62f45" alt="labs: 1 live" height="20">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/docker-dark.svg?v=2b6c885f">
    <img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/docker-light.svg?v=d7abbc30" alt="docker: compose v2" height="20">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/checker-dark.svg?v=cff908fc">
    <img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/checker-light.svg?v=6052eb0b" alt="checker: python3" height="20">
  </picture>
</p>

Open-source cybersecurity labs that run in Docker. Each lab is a
self-contained exercise: one vulnerable service, one brief, one flag
inside. You solve on your own machine, at your own pace. No accounts, no
scoring server.

## What openlabs is

A lab library, not a platform. Each entry under `labs/<track>/<lab>/` is a
reproducible Docker Compose setup with a story, a goal, and a flag. The
repository stores the SHA-256 hash of each flag, never the plaintext.
Reading lab source to find the flag is a legitimate solve.

This wiki serves three audiences.

<div align="center">

| You are | Start here |
|:---:|:---|
| A player | [Getting Started](Getting-Started) |
| A content writer | [Authoring a Lab](Authoring-a-Lab) |
| A reviewer | [Reviewer Checklist](Reviewer-Checklist) |

</div>

## The ground rules

- Labs run offline once images are pulled. No runtime network calls.
- One documented host port per lab.
- Flags follow the `duck{...}` format. The hash ships; the plaintext stays
  inside lab internals.
- Written content follows one voice: short declaratives, no hype.

## Quick links

```bash
git clone https://github.com/Duckurity/openlabs
cd openlabs/labs/web/duck-cross
docker compose up -d
```

Open `http://localhost:8080`. Verify a solve with
`python3 scripts/check.py labs/web/duck-cross`.

[Explore the repository](https://github.com/Duckurity/openlabs) |
[Report a broken lab](https://github.com/Duckurity/openlabs/issues)
