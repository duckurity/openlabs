# AGENTS.md

Entry point for coding agents working in this repository.

## What this repo is

openlabs is a library of self-contained, Docker-based cybersecurity labs.
Each lab is a directory under `labs/<track>/<lab>/` holding `lab.yml`
metadata, a player-facing `README.md`, a compose file, and the lab service.
`scripts/validate.py` checks structure and metadata; `scripts/check.py`
verifies a player's flag against the stored SHA-256 hash.

## Structure

| Path | What it is |
|---|---|
| `labs/<track>/<lab>/` | one lab; tracks: `web`, `binary`, `crypto`, `network`, `osint` |
| `labs/_template/` | skeleton for new labs, skipped by validation |
| `scripts/validate.py` | CI validator, zero dependencies |
| `scripts/check.py` | player flag checker, zero dependencies |
| `wiki/` | GitHub wiki source: player, authoring, and review guides |
| `.github/workflows/labs.yml` | CI, runs the validator on labs and scripts changes |

## Voice rules for any text you write

- Short declarative sentences. Lead with the verb. One idea per sentence.
- Sentence case for headings.
- No exclamation marks, no em-dashes, no superlatives, no adverbs, no
  hacker-larp phrasing ("pwn", "1337").
- Terms: `lab`, `flag`, `solve`, `writeup`. Difficulty: `easy`, `medium`,
  `hard`, `insane`, lowercase in prose, uppercase only in mono badges.
- Put values in code spans: ports, commands, formats.

## Hard rules

- Flag format: `^duck\{[a-z0-9_]{16,40}\}$`. Plaintext flags appear only
  inside lab service files, never in `lab.yml`, lab `README.md`, `wiki/`,
  or anything outside `labs/`.
- Base images pinned to full version tags. No runtime network calls.
- One documented host port per lab.
- Code is Apache-2.0, written content is CC-BY-4.0. Do not relicense.

## Commands

```bash
python3 scripts/validate.py              # structure + metadata
python3 scripts/validate.py --compose    # + docker compose config
python3 scripts/check.py labs/web/duck-cross
```
