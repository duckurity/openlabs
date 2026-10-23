# OpenLabs state and logs

OpenLabs keeps operational data under `.openlabs/` at the repository root. The
directory is gitignored. Nothing in this tree should contain plaintext flags,
raw `flag_hash` values, tokens, or credentials.

## Layout

```text
.openlabs/
  config.json
  state/<lab-slug>.json
  logs/<lab>/<run-id>.log
  bundles/<timestamp>.json
```

| Path | Purpose |
|:---|:---|
| `config.json` | Repo-level OpenLabs configuration after `setup` |
| `state/<lab>.json` | Per-lab lifecycle state (`openlabs.state.v1`) |
| `logs/<lab>/` | Redacted command logs per run |
| `bundles/` | Redacted diagnostic bundles from `issue bundle` |

## Lifecycle states

State files record a `lifecycle` field. Common values:

| State | Meaning |
|:---|:---|
| `unconfigured` | No durable configuration for this lab |
| `configured` | Project, port, and paths resolved; containers not running |
| `building` | Image build in progress |
| `starting` | Containers up; readiness not proven |
| `ready` | Readiness checks passed |
| `stopped` | Containers stopped; configuration reusable by `lab start` |
| `failed` | Last mutation failed; diagnostics preserved |
| `resetting` | Teardown in progress |

If a command stops mid-run, state stays at the last honest phase. You may see
`OL-0038`. Run `./openlabs lab status <lab>` to reconcile with Compose.

## Cleanup and rollback

| Action | Scope |
|:---|:---|
| `lab stop` | Stops namespaced containers. Keeps state for `lab start`. |
| `lab reset` | Removes namespaced compose resources for the lab project recorded in state. Does not delete lab source, git metadata, or notes outside the lab tree. |
| `doctor --fix` | Repo-local OpenLabs files only. Never prunes unrelated Docker objects. |

Registry rollback note for interrupted state: reset removes only the OpenLabs
compose project when policy allows. See `OL-0038` in [CLI troubleshooting](CLI-Troubleshooting).

## Redaction

CLI output, logs, and bundles pass through the same rules as
`scripts/diagnostic_registry.py`:

- Plaintext flags become `<redacted-flag>`
- 64-character hex digests become `<hash>`
- Bearer tokens and common secret patterns become redacted placeholders
- Home directory paths become `<path>`

JSON envelopes may set `meta.redacted: true` when any field was redacted.

Do not disable redaction when sharing bundles or CI artifacts.

## Manual recovery

When automated recovery is unclear:

1. Run `./openlabs lab status <lab>` with `--json`.
2. Inspect `.openlabs/logs/<lab>/` for the latest run id.
3. Run `./openlabs issue explain OL-####` for each diagnostic id.
4. Prefer `./openlabs lab reset <lab>` only when you accept teardown of the
   namespaced project.

For supported reference behavior on Tier 1, follow [OpenLabs CLI](OpenLabs-CLI).
