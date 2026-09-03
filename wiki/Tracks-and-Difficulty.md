## Tracks

Five tracks, each a family of weakness. A lab belongs to exactly one track,
set in `lab.yml` and mirrored by its directory under `labs/`.

| Track | Focus |
|---|---|
| `web` | injection, broken access control, auth bypass, SSRF |
| `binary` | memory corruption, exploitation, reverse engineering |
| `crypto` | weak primitives, protocol misuse, implementation faults |
| `network` | protocol abuse, traffic analysis, pivoting |
| `osint` | recon, source analysis, signature tracing |

Choose the track that names the primary weakness. A lab may touch others,
but one track leads.

## Difficulty

Grades describe what a player does, not how long it takes. Four tiers,
uppercase in mono badges, lowercase in prose.

| Level | Expectation |
|---|---|
| `EASY` | one vector, minimal recon, the brief points at the surface |
| `MEDIUM` | chained steps, some enumeration, the vector needs a decision |
| `HARD` | multiple systems or stages, custom tooling, dead ends that punish assumptions |
| `INSANE` | research-level, an original technique, no public reference walkthrough |

## Grading rules

- Pick one tier.
- Grade the action, not the clock. A slow easy lab is still easy.
- If a lab sits between two tiers, grade down. Let the solve rate correct
  it later.

The difficulty value is a promise to the player. Understating it wastes
their time; overstating it breaks their trust.
