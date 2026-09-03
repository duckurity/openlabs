Open-source cybersecurity labs that run in Docker. Each lab is a
self-contained exercise: one vulnerable service, one brief, one flag
inside. You solve on your own machine, at your own pace. No accounts, no
scoring server. Open another tab and exploit a lab to see what a solve
feels like.

## What openlabs is

A lab library, not a platform. Each entry under `labs/<track>/<lab>/` is a
reproducible Docker Compose setup with a story, a goal, and a flag. The
repository stores the SHA-256 hash of each flag, never the plaintext.
Reading lab source to find the flag is a legitimate solve.

The project has three audiences, and this wiki serves each one.

| You are | Start here |
|---|---|
| A player | [Getting Started](Getting-Started) |
| A content writer | [Authoring a Lab](Authoring-a-Lab) |
| A reviewer | [Reviewer Checklist](Reviewer-Checklist) |

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
