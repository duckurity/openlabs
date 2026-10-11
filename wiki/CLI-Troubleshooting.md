# CLI troubleshooting

Index of M2 runtime diagnostics (`OL-0034` through `OL-0046`). Contract parse
and schema ids (`OL-0001` through `OL-0033`) come from lab validation; see
[M1 contract v1 freeze](M1-09-Contract-v1-Freeze).

Look up any id locally:

```bash
./openlabs issue explain OL-0040
```

| Id | Key | Summary |
|:---|:---|:---|
| [OL-0034](#ol-0034) | `lifecycle.interaction.non_interactive_required` | Command needs confirmation but `--non-interactive` is set |
| [OL-0035](#ol-0035) | `lifecycle.platform.unsupported_architecture` | Host architecture is not supported for guaranteed lifecycle |
| [OL-0036](#ol-0036) | `lifecycle.port.conflict` | Requested host port is occupied |
| [OL-0037](#ol-0037) | `lifecycle.compose.unsafe_container_name` | Compose declares `container_name` |
| [OL-0038](#ol-0038) | `lifecycle.state.interrupted` | Previous lifecycle command stopped mid-transaction |
| [OL-0039](#ol-0039) | `lifecycle.lab.unsupported_operation` | Lab status or compose safety blocks the operation |
| [OL-0040](#ol-0040) | `environment.docker.client_missing` | Docker client binary not on PATH |
| [OL-0041](#ol-0041) | `environment.docker.daemon_unavailable` | Docker daemon not reachable |
| [OL-0042](#ol-0042) | `lifecycle.cli.usage` | Command line usage is invalid |
| [OL-0043](#ol-0043) | `lifecycle.cli.internal` | Unexpected internal CLI failure |
| [OL-0044](#ol-0044) | `lifecycle.cli.not_implemented` | Command slice not shipped in this milestone |
| [OL-0045](#ol-0045) | `environment.repo.layout_invalid` | Not inside an OpenLabs repository root |
| [OL-0046](#ol-0046) | `lifecycle.cli.unknown_diagnostic` | Diagnostic id is not registered |

Platform context: [Platform support tiers](Platform-Support-Tiers).

## OL-0034

**Key:** `lifecycle.interaction.non_interactive_required`

**Cause:** Command needs confirmation but `--non-interactive` is set.

**When:** You run a mutating command with `--non-interactive` that would prompt
for confirmation (for example destructive `lab reset` under policy).

**Evidence:**

- Re-run without `--non-interactive`
- Provide explicit flags documented in [OpenLabs CLI](OpenLabs-CLI)

**Safe action:** Remove `--non-interactive` when the command requires confirmation.

**Manual action:** Run the command interactively or supply documented
non-interactive flags.

```bash
./openlabs issue explain OL-0034
```

## OL-0035

**Key:** `lifecycle.platform.unsupported_architecture`

**Cause:** Host architecture is not supported for guaranteed lifecycle on this lab.

**When:** You request a guaranteed lifecycle command on Tier 3 hardware without
per-lab evidence.

**Evidence:**

- Check `uname -m` output
- Review [Platform support tiers](Platform-Support-Tiers)

**Manual action:** Use a Tier 1 Linux `x86_64` host or wait for per-lab evidence
on this architecture.

```bash
./openlabs issue explain OL-0035
```

## OL-0036

**Key:** `lifecycle.port.conflict`

**Cause:** Requested host port is occupied and policy forbids silent reassignment.

**When:** You bind a host port for `lab setup` or `lab start` and the port is in use.

**Evidence:**

- Check listeners on the requested port
- Inspect `.openlabs/state` for `host_port` when present

**Safe action:** Pick a free port when policy allows automatic selection.

**Manual action:** Stop the conflicting service or pass `--port` with a free port.

```bash
./openlabs issue explain OL-0036
```

## OL-0037

**Key:** `lifecycle.compose.unsafe_container_name`

**Cause:** Compose file declares `container_name`, which breaks OpenLabs namespacing.

**When:** Lifecycle mutation runs against a compose file with `container_name`.

**Evidence:**

- Search the compose file for `container_name`
- Run `./openlabs lab list` and read blockers

**Manual action:** Remove `container_name` in a lab fix pull request or choose
a supported lab.

```bash
./openlabs issue explain OL-0037
```

## OL-0038

**Key:** `lifecycle.state.interrupted`

**Cause:** Previous lifecycle command stopped mid-transaction; state must be reconciled.

**When:** A prior command exited on signal, timeout, or crash.

**Evidence:**

- Run `./openlabs lab status <lab>`
- Check `.openlabs/logs` for the partial run

**Safe action:** Run `./openlabs lab status` to reconcile state.

**Manual action:** Run `./openlabs lab reset` then `lab setup` when policy allows.

**Rollback:** Reset removes only the OpenLabs compose project.

```bash
./openlabs issue explain OL-0038
```

## OL-0039

**Key:** `lifecycle.lab.unsupported_operation`

**Cause:** Lab status or compose safety blocks a guaranteed lifecycle operation.

**When:** You request a guaranteed lifecycle operation on an experimental lab or
a lab with blockers.

**Evidence:**

- Run `./openlabs lab list` and read blockers
- Confirm lab `status` is `supported` for the full path

**Manual action:** Use `duck-cross` for the supported lifecycle path or run
maintainer scripts only.

```bash
./openlabs issue explain OL-0039
```

## OL-0040

**Key:** `environment.docker.client_missing`

**Cause:** Docker client binary is not available on PATH.

**When:** Any command needs the Docker client.

**Evidence:**

- Run `docker --version`
- Confirm `docker` is on PATH

**Manual action:** Install Docker Engine or Docker Desktop per platform docs.
OpenLabs does not install Docker for you.

```bash
./openlabs issue explain OL-0040
```

## OL-0041

**Key:** `environment.docker.daemon_unavailable`

**Cause:** Docker daemon is not reachable.

**When:** The client exists but `docker info` fails.

**Evidence:**

- Run `docker info`
- Confirm the daemon service is running

**Manual action:** Start Docker Engine or Docker Desktop and retry.

```bash
./openlabs issue explain OL-0041
```

## OL-0042

**Key:** `lifecycle.cli.usage`

**Cause:** Command line usage is invalid.

**When:** Unknown subcommand, bad flag order, or missing arguments.

**Evidence:**

- Run `./openlabs --help`
- Compare argv with [OpenLabs CLI](OpenLabs-CLI)

**Safe action:** Fix argv ordering and command spelling. Put global flags before
the subcommand.

```bash
./openlabs issue explain OL-0042
```

## OL-0043

**Key:** `lifecycle.cli.internal`

**Cause:** Unexpected internal CLI failure.

**When:** An uncaught error escapes the CLI envelope (report a bug).

**Evidence:**

- Re-run with `--json`
- Run `./openlabs issue bundle` and inspect diagnostics

**Manual action:** File a bug with the redacted bundle. Do not paste secrets.

```bash
./openlabs issue explain OL-0043
```

## OL-0044

**Key:** `lifecycle.cli.not_implemented`

**Cause:** Command behavior is not implemented in this milestone slice.

**When:** You call a command planned for a later milestone.

**Evidence:**

- Check [M2 lifecycle decisions](M2-Lifecycle-Decisions) and [M2 release evidence](M2-Release-Evidence)

**Manual action:** Use documented repository scripts until the CLI slice ships.

```bash
./openlabs issue explain OL-0044
```

## OL-0045

**Key:** `environment.repo.layout_invalid`

**Cause:** Current directory is not inside an OpenLabs repository root.

**When:** You run `openlabs` outside a checkout.

**Evidence:**

- Confirm `AGENTS.md` exists in the current tree
- Clone the openlabs repository

**Manual action:** `cd` into the repository root and retry.

```bash
./openlabs issue explain OL-0045
```

## OL-0046

**Key:** `lifecycle.cli.unknown_diagnostic`

**Cause:** Diagnostic id is not registered.

**When:** `issue explain` receives an id not in `contracts/diagnostics.json`.

**Evidence:**

- Run `./openlabs issue explain OL-####` with a valid id
- Search `contracts/diagnostics.json`

**Safe action:** Use an id from the registry.

**Manual action:** Upgrade openlabs if the id comes from a newer milestone.

```bash
./openlabs issue explain OL-0046
```
