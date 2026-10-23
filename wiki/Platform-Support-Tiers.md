# Platform support tiers

OpenLabs classifies your host and each lab before it mutates Docker or writes
state. The CLI never installs Docker, changes system groups, or edits global
network settings.

Decision record: [M2 lifecycle decisions](M2-Lifecycle-Decisions).
Catalog policy: [Lab catalog status](Lab-Catalog-Status).

## Tier 1 (owned evidence)

| Item | Policy |
|:---|:---|
| Host | Linux `x86_64` |
| Python | 3.12 or newer |
| Container runtime | Docker Engine with Compose v2 |
| Lifecycle guarantee | `duck-cross` only (`status: supported`) |
| CI | Job **Prove duck-cross L0-L6** runs legacy prove and Tier 1 CLI lifecycle evidence |

A clean Tier 1 player follows [OpenLabs CLI](OpenLabs-CLI) from clone to ready
`duck-cross`.

## Tier 2 (detect and guide)

| Item | Policy |
|:---|:---|
| Hosts | WSL2, macOS on Intel (`Darwin`/`x86_64`) with Docker Desktop |
| CLI behavior | Detect tier, run diagnostics, document next steps |
| Release guarantee | No release guarantee without hosted runner evidence on these platforms |
| Missing evidence | No required CI matrix on WSL2 or macOS at M2 release |

Tier 2 may run many commands successfully. Failures still map to `OL-####`
diagnostics. Do not treat Tier 2 as equivalent to Tier 1 until evidence is
published on the [M2 release evidence](M2-Release-Evidence) page.

## Tier 3 (early detect)

| Item | Policy |
|:---|:---|
| Hosts | Linux ARM64, Apple Silicon (`Darwin`/`arm64`) |
| CLI behavior | Detect architecture early |
| Lifecycle | Per-lab evidence required; otherwise expect `OL-0035` |
| Missing evidence | No ARM64 lifecycle guarantee at M2 release |

## Experimental labs

The catalog lists **19 experimental** labs. They appear in `lab list` with
status and blockers. OpenLabs does **not** guarantee `lab setup`, `start`,
`verify`, `reset`, or `stop` for them. Mutations return `OL-0039` when the lab
status or compose safety rules block the operation.

Experimental labs are not lifecycle-guaranteed. Use maintainer scripts or manual
compose only when you accept that risk.

## Uncatalogued directories

Directories under `labs/` without valid catalog metadata are excluded from
`lab list` and from CLI lab selection.

## Unsupported runtimes

Podman and similar runtimes are not assumed Docker-compatible. The CLI may
detect and guide only. Do not expect parity with Docker Engine behavior.

## Related diagnostics

| Id | When |
|:---|:---|
| `OL-0035` | Guaranteed lifecycle on unsupported CPU architecture |
| `OL-0039` | Guaranteed operation blocked for experimental or unsafe lab |
| `OL-0040` | Docker client missing |
| `OL-0041` | Docker daemon unavailable |
| `OL-0045` | Command run outside repository root |

Full index: [CLI troubleshooting](CLI-Troubleshooting).
