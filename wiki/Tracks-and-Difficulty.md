## Tracks

Five tracks, each a family of weakness. A lab belongs to exactly one track,
set in `lab.yml` and mirrored by its directory under `labs/`.

<div align="center">

| Track | Focus |
|:---:|:---|
| `web` | injection, broken access control, auth bypass, SSRF |
| `binary` | memory corruption, exploitation, reverse engineering |
| `crypto` | weak primitives, protocol misuse, implementation faults |
| `network` | protocol abuse, traffic analysis, pivoting |
| `osint` | recon, source analysis, signature tracing |

</div>

Choose the track that names the primary weakness. A lab may touch others,
but one track leads.

## Difficulty

Grades describe what a player does, not how long it takes. Four tiers,
uppercase in mono badges, lowercase in prose.

<div align="center">

| Level | Expectation |
|:---:|:---|
| <picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/chip-easy-dark.svg?v=1"><img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/chip-easy-light.svg?v=1" alt="EASY" height="18"></picture> | one vector, minimal recon, the brief points at the surface |
| <picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/chip-medium-dark.svg?v=1"><img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/chip-medium-light.svg?v=1" alt="MEDIUM" height="18"></picture> | chained steps, some enumeration, the vector needs a decision |
| <picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/chip-hard-dark.svg?v=1"><img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/chip-hard-light.svg?v=1" alt="HARD" height="18"></picture> | multiple systems or stages, custom tooling, dead ends that punish assumptions |
| <picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/chip-insane-dark.svg?v=1"><img src="https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges/chip-insane-light.svg?v=1" alt="INSANE" height="18"></picture> | research-level, an original technique, no public reference walkthrough |

</div>

## Grading rules

- Pick one tier.
- Grade the action, not the clock. A slow easy lab is still easy.
- If a lab sits between two tiers, grade down. Let the solve rate correct
  it later.

The difficulty value is a promise to the player. Understating it wastes
their time; overstating it breaks their trust.
