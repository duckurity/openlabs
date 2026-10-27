# M2 release evidence

Completion record for milestone **M2 - One-command lab lifecycle** and [#133 M2-10](https://github.com/duckurity/openlabs/issues/133).

Reviewed on `2026-10-24`. Regenerate with `python3 scripts/m2_release_report.py --write-wiki wiki/M2-Release-Evidence.md`.

## Release markers

| Item | Value |
|:---|:---|
| CLI version | `0.2.0` |
| Command envelope | `openlabs.command.v1` |
| Lab contract | `1` |
| Reviewed commit | `944da66a89fb` |
| Release evidence commit | `d6ebe8116452` |

## Supported manifest

- Supported: **1**
- Experimental: **20**
- Catalogued: **21**

| Path | Name | Reference |
|:---|:---|:---|
| `labs/web/duck-cross` | duck-cross | yes |

## Platform and CI evidence

- Tier 1 platform: Linux x86_64 with Python 3.12, Docker Engine, Compose v2
- Reference lab: `labs/web/duck-cross`
- Hosted CI run: [https://github.com/duckurity/openlabs/actions/runs/37861671412](https://github.com/duckurity/openlabs/actions/runs/37861671412) (success)
- Tier 1 proof job: [Prove duck-cross L0-L6](https://github.com/duckurity/openlabs/actions/runs/37861671412/job/113598670443)
- Release evidence commit: `d6ebe811645282d4a53341543887527c43146e5b`
- Uploaded artifacts: `reference-lab-evidence`, `m2-tier1-lifecycle-evidence`

CI job **Prove duck-cross L0-L6** runs:

1. `python3 scripts/prove_reference_lab.py` (legacy L0–L6 prove)
2. Bounded prove artifact via `scripts/evidence_artifact.py`
3. `python3 scripts/run_m2_tier1_lifecycle.py` (CLI lifecycle evidence)
4. Secret scan on both JSON artifacts

### Tier 1 CLI lifecycle timings (hosted)

| Step | Ok | Seconds |
|:---|:---:|---:|
| `lab_setup` | yes | 1.53 |
| `lab_verify` | yes | 33.38 |
| `lab_reset` | yes | 0.19 |
| `lab_start` | yes | 0.89 |
| `lab_status` | yes | 0.19 |
| `lab_stop` | yes | 10.39 |

### Reset and second start proof

- `lab_reset` completed in **0.19s**
- `lab_start` completed in **0.89s** (second start after verify reset cycle)
- Cleanup ok: **True**

Tier 1 CLI lifecycle command order:

- `./openlabs --json --non-interactive lab setup duck-cross`
- `./openlabs --json --non-interactive lab verify duck-cross`
- `./openlabs --json --non-interactive lab reset duck-cross`
- `./openlabs --json --non-interactive lab start duck-cross`
- `./openlabs --json --non-interactive lab status duck-cross`
- `./openlabs --json --non-interactive lab stop duck-cross`

## Player and maintainer docs

- [OpenLabs CLI](OpenLabs-CLI)
- [Platform support tiers](Platform-Support-Tiers)
- [OpenLabs state and logs](OpenLabs-State-and-Logs)
- [CLI troubleshooting](CLI-Troubleshooting)

## Known limitations

- Only duck-cross has a Tier 1 lifecycle guarantee
- Nineteen experimental labs lack full lifecycle support
- Tier 2 and Tier 3 hosts lack hosted runner lifecycle evidence at release
- Eight experimental labs declare container_name and block lifecycle mutation
- Legacy prove_reference_lab.py runs beside CLI Tier 1 evidence until prove removal
- issue bundle records invocation and evidence paths but does not replay prior command diagnostics automatically

## Deferred work

- PyPI or standalone package publish
- M3 AI-assisted tooling
- M4 assignment automation
- Automatic OS package installation
- Podman parity with Docker Engine
- Promoting experimental labs to supported without evidence
- Native Windows outside WSL2

## M2 delivery checklist

| Step | Issue | Evidence |
|:---:|:---|:---|
| M2-01 | [#124](https://github.com/duckurity/openlabs/issues/124) | contracts/cli-v1.md; scripts/fixtures/cli_contract/ |
| M2-02 | [#125](https://github.com/duckurity/openlabs/issues/125) | ./openlabs; scripts/openlabs_cli/ |
| M2-03 | [#126](https://github.com/duckurity/openlabs/issues/126) | contracts/diagnostics.json OL-0034+; issue explain/bundle |
| M2-04 | [#127](https://github.com/duckurity/openlabs/issues/127) | openlabs lab list |
| M2-05 | [#128](https://github.com/duckurity/openlabs/issues/128) | openlabs setup; openlabs doctor |
| M2-06 | [#129](https://github.com/duckurity/openlabs/issues/129) | .openlabs/ state; lab setup transaction |
| M2-07 | [#130](https://github.com/duckurity/openlabs/issues/130) | lab start/status/stop/reset commands |
| M2-08 | [#131](https://github.com/duckurity/openlabs/issues/131) | lab verify; prove_reference_lab.py |
| M2-09 | [#132](https://github.com/duckurity/openlabs/issues/132) | labs.yml reference-lab dual evidence; test_m2.py |
| M2-10 | [#133](https://github.com/duckurity/openlabs/issues/133) | wiki/OpenLabs-CLI.md; wiki/M2-Release-Evidence.md |

## Release approval (manual)

Senior maintainer approval is required before closing #133.

| Reviewer | Date | Outcome | Notes |
|:---|:---|:---|:---|
| _pending_ | _pending_ | _pending_ | Senior maintainer signs M2 release boundary on issue #133 before close |
