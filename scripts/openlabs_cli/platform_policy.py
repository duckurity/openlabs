"""Host tier checks for guaranteed lifecycle commands."""

from __future__ import annotations

from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic
from openlabs_cli.environment_probe import run_environment_probe
from openlabs_cli.repo_config import load_config

BLOCKED_GUARANTEED_TIERS = frozenset({"tier3", "unsupported"})


def resolve_host_tier(ctx: CliContext) -> str:
    config = load_config(ctx.repo_root)
    if config and isinstance(config.get("tier"), str):
        return config["tier"]
    return run_environment_probe(ctx).tier


def guaranteed_lifecycle_block(
    ctx: CliContext,
    *,
    action: str,
    lab: str | None = None,
) -> CliResult | None:
    tier = resolve_host_tier(ctx)
    if tier not in BLOCKED_GUARANTEED_TIERS:
        return None
    slug = lab or "duck-cross"
    message = (
        "host tier does not include guaranteed lifecycle evidence for this lab; "
        "use Tier 1 Linux x86_64 or wait for per-lab evidence"
    )
    return CliResult(
        command="lab",
        ok=False,
        exit_code=1,
        data={"action": action, "lab": slug, "tier": tier},
        diagnostics=[Diagnostic("lifecycle.platform.unsupported_architecture", message)],
        human_lines=[message],
    )
