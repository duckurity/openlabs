"""Lab start, status, stop, and reset (M2-07)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openlabs_cli.compose_ops import compose_argv_from_state, planned_compose_step
from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic
from openlabs_cli.errors import UsageError
from openlabs_cli.lab_discovery import LabSelectionError, ResolvedLab, resolve_lab
from openlabs_cli.lab_runtime import compose_running, run_compose, wait_ready
from openlabs_cli.namespace import compose_project_name
from openlabs_cli.state_store import (
    LabLockError,
    build_state_payload,
    lab_lock,
    load_state,
    write_state,
)

START_COMPATIBLE = frozenset({"configured", "stopped", "ready", "failed"})
INTERRUPTED_LIFECYCLES = frozenset({"building", "starting", "resetting"})


def _usage(action: str) -> UsageError:
    if action == "reset":
        return UsageError("usage: openlabs lab reset <lab> [--volumes] [--yes]")
    return UsageError(f"usage: openlabs lab {action} <lab>")


def _split_reset_args(args: list[str]) -> tuple[str, bool, bool]:
    flags: list[str] = []
    positional: list[str] = []
    for item in args:
        if item.startswith("--"):
            flags.append(item)
        else:
            positional.append(item)
    if len(positional) != 1:
        raise _usage("reset")
    remove_volumes = "--volumes" in flags
    confirm = "--yes" in flags
    unknown = [flag for flag in flags if flag not in {"--volumes", "--yes"}]
    if unknown:
        raise UsageError(f"unknown option(s): {', '.join(unknown)}")
    return positional[0], remove_volumes, confirm


def _resolve(ctx: CliContext, selector: str) -> ResolvedLab | CliResult:
    selection = resolve_lab(ctx.repo_root, selector)
    if isinstance(selection, LabSelectionError):
        from openlabs_cli.commands.lab import selection_failure

        return selection_failure(selection)
    return selection


def _mutation_blockers(resolved: ResolvedLab, *, action: str) -> CliResult | None:
    entry = resolved.entry
    slug = entry["slug"]
    if entry.get("blockers") and "container_name" in entry["blockers"]:
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": action, "lab": slug, "blockers": entry["blockers"]},
            diagnostics=[
                Diagnostic(
                    "lifecycle.compose.unsafe_container_name",
                    "compose file declares container_name; lifecycle mutation blocked",
                )
            ],
            human_lines=["compose declares container_name; choose a supported lab"],
        )
    if entry.get("status") != "supported":
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": action, "lab": slug},
            diagnostics=[
                Diagnostic(
                    "lifecycle.lab.unsupported_operation",
                    "only supported labs implement openlabs lab lifecycle in this milestone",
                )
            ],
            human_lines=["lab is not eligible for guaranteed lifecycle commands"],
        )
    return None


def _interrupted_result(*, action: str, slug: str, lifecycle: str, command: str) -> CliResult:
    message = "previous lab setup stopped mid-build; run lab status then lab reset or lab setup"
    if lifecycle == "resetting":
        message = "previous lab reset stopped mid-teardown; run lab status then lab reset"
    elif lifecycle == "starting":
        message = "previous lab start stopped mid-run; run lab status then lab reset or lab start"
    return CliResult(
        command="lab",
        ok=False,
        exit_code=1,
        data={
            "action": action,
            "lab": slug,
            "lifecycle": lifecycle,
            "interrupted_command": command,
        },
        diagnostics=[Diagnostic("lifecycle.state.interrupted", message)],
        human_lines=[message],
    )


def _compose_status(ctx: CliContext, *, lab_dir: Path, state: dict[str, Any]) -> str:
    argv = compose_argv_from_state(ctx.repo_root, lab_dir=lab_dir, state=state, subcommand=["ps", "-q"])
    code, out = run_compose(ctx, argv, timeout=30.0)
    if code != 0:
        return "missing"
    return "running" if out.strip() else "stopped"


def _project_for_dry_run(ctx: CliContext, slug: str, state: dict[str, Any] | None) -> str:
    if state:
        return str(state["compose_project"])
    return compose_project_name(ctx.repo_root, slug)


def _require_state(action: str, slug: str, state: dict[str, Any] | None) -> CliResult | dict[str, Any]:
    if state is None:
        message = "lab has no OpenLabs state; run openlabs lab setup first"
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": action, "lab": slug, "lifecycle": "unconfigured"},
            diagnostics=[Diagnostic("lifecycle.cli.usage", message)],
            human_lines=[message],
        )
    return state


def handle_lab_start(ctx: CliContext, args: list[str]) -> CliResult:
    if len(args) != 1:
        raise _usage("start")
    resolved = _resolve(ctx, args[0])
    if isinstance(resolved, CliResult):
        return resolved
    blocked = _mutation_blockers(resolved, action="start")
    if blocked:
        return blocked
    slug = resolved.entry["slug"]
    lab_dir = resolved.lab_dir
    state = load_state(ctx.repo_root, slug)
    lifecycle = str(state["lifecycle"]) if state else "unconfigured"
    project = _project_for_dry_run(ctx, slug, state)

    if ctx.dry_run:
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "start",
                "lab": slug,
                "project": project,
                "lifecycle": lifecycle,
                "planned": [planned_compose_step(["up", "-d"])],
            },
            human_lines=["lab start dry-run: no containers changed"],
            meta={"reset_safe": True},
        )

    required = _require_state("start", slug, state)
    if isinstance(required, CliResult):
        return required
    state = required
    lifecycle = str(state["lifecycle"])
    project = str(state["compose_project"])

    if lifecycle in INTERRUPTED_LIFECYCLES:
        return _interrupted_result(action="start", slug=slug, lifecycle=lifecycle, command="lab setup")

    if lifecycle not in START_COMPATIBLE:
        message = f"lab lifecycle {lifecycle!r} cannot start; run lab status or lab reset"
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "start", "lab": slug, "lifecycle": lifecycle},
            diagnostics=[Diagnostic("lifecycle.cli.usage", message)],
            human_lines=[message],
        )

    host_port = int(state["host_port"])
    base_url = f"http://127.0.0.1:{host_port}"
    argv_prefix = compose_argv_from_state(
        ctx.repo_root, lab_dir=lab_dir, state=state, subcommand=[]
    )
    if lifecycle == "ready" and compose_running(ctx, argv_prefix):
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "start",
                "lab": slug,
                "project": project,
                "lifecycle": "ready",
                "already_running": True,
                "url": f"{base_url}/",
            },
            human_lines=[f"lab {slug} already running at {base_url}/"],
            meta={"reset_safe": True},
        )

    try:
        with lab_lock(ctx.repo_root, slug):
            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=host_port,
                    lifecycle="starting",
                    compose_file=str(state["compose_file"]),
                    container_port=int(state["container_port"]),
                ),
            )
            up_argv = compose_argv_from_state(
                ctx.repo_root, lab_dir=lab_dir, state=state, subcommand=["up", "-d"]
            )
            code, detail = run_compose(ctx, up_argv, timeout=300.0)
            if code != 0 or ctx.interrupted:
                write_state(
                    ctx.repo_root,
                    build_state_payload(
                        slug=slug,
                        compose_project=project,
                        host_port=host_port,
                        lifecycle="starting",
                        compose_file=str(state["compose_file"]),
                        container_port=int(state["container_port"]),
                    ),
                )
                if ctx.interrupted:
                    return _interrupted_result(
                        action="start", slug=slug, lifecycle="starting", command="lab start"
                    )
                return CliResult(
                    command="lab",
                    ok=False,
                    exit_code=1,
                    data={"action": "start", "lab": slug, "project": project, "detail": detail},
                    diagnostics=[Diagnostic("lifecycle.cli.internal", "compose up failed during lab start")],
                    human_lines=["compose up failed during lab start"],
                )
            if not wait_ready(base_url):
                write_state(
                    ctx.repo_root,
                    build_state_payload(
                        slug=slug,
                        compose_project=project,
                        host_port=host_port,
                        lifecycle="failed",
                        compose_file=str(state["compose_file"]),
                        container_port=int(state["container_port"]),
                    ),
                )
                return CliResult(
                    command="lab",
                    ok=False,
                    exit_code=1,
                    data={"action": "start", "lab": slug, "lifecycle": "failed"},
                    diagnostics=[Diagnostic("lifecycle.cli.internal", "lab service did not become ready in time")],
                    human_lines=["lab service did not become ready in time"],
                )
            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=host_port,
                    lifecycle="ready",
                    compose_file=str(state["compose_file"]),
                    container_port=int(state["container_port"]),
                ),
            )
    except LabLockError as exc:
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "start", "lab": slug},
            diagnostics=[Diagnostic("lifecycle.cli.internal", str(exc))],
            human_lines=[str(exc)],
        )

    return CliResult(
        command="lab",
        ok=True,
        exit_code=0,
        data={
            "action": "start",
            "lab": slug,
            "project": project,
            "lifecycle": "ready",
            "url": f"{base_url}/",
        },
        human_lines=[f"lab {slug} is running at {base_url}/"],
        meta={"reset_safe": True},
    )


def handle_lab_status(ctx: CliContext, args: list[str]) -> CliResult:
    if len(args) != 1:
        raise _usage("status")
    resolved = _resolve(ctx, args[0])
    if isinstance(resolved, CliResult):
        return resolved
    slug = resolved.entry["slug"]
    lab_dir = resolved.lab_dir
    state = load_state(ctx.repo_root, slug)
    if state is None:
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "status",
                "lab": slug,
                "lifecycle": "unconfigured",
                "recorded": "unconfigured",
                "compose": "missing",
                "drift": False,
            },
            human_lines=[f"lab {slug} has no OpenLabs state"],
            meta={"reset_safe": True},
        )

    recorded = str(state["lifecycle"])
    if recorded in INTERRUPTED_LIFECYCLES or recorded == "building":
        return _interrupted_result(action="status", slug=slug, lifecycle=recorded, command="lab setup")

    compose = _compose_status(ctx, lab_dir=lab_dir, state=state)
    drift = False
    if recorded == "ready" and compose != "running":
        drift = True
    elif recorded == "stopped" and compose == "running":
        drift = True
    elif recorded in {"configured", "stopped"} and compose == "missing":
        drift = recorded == "stopped"

    host_port = int(state["host_port"])
    data: dict[str, Any] = {
        "action": "status",
        "lab": slug,
        "lifecycle": recorded if not drift else recorded,
        "recorded": recorded,
        "compose": compose,
        "drift": drift,
    }
    if recorded == "ready" and compose == "running":
        data["url"] = f"http://127.0.0.1:{host_port}/"
    human = [f"lab {slug} recorded {recorded}; compose {compose}"]
    if drift:
        human.append("state drift detected; run lab start, lab stop, or lab reset to reconcile")
    return CliResult(
        command="lab",
        ok=True,
        exit_code=0,
        data=data,
        human_lines=human,
        meta={"reset_safe": True},
    )


def handle_lab_stop(ctx: CliContext, args: list[str]) -> CliResult:
    if len(args) != 1:
        raise _usage("stop")
    resolved = _resolve(ctx, args[0])
    if isinstance(resolved, CliResult):
        return resolved
    blocked = _mutation_blockers(resolved, action="stop")
    if blocked:
        return blocked
    slug = resolved.entry["slug"]
    lab_dir = resolved.lab_dir
    state = load_state(ctx.repo_root, slug)
    project = _project_for_dry_run(ctx, slug, state)

    if ctx.dry_run:
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "stop",
                "lab": slug,
                "project": project,
                "planned": [planned_compose_step(["stop"])],
            },
            human_lines=["lab stop dry-run: no containers changed"],
            meta={"reset_safe": True},
        )

    required = _require_state("stop", slug, state)
    if isinstance(required, CliResult):
        return required
    state = required
    project = str(state["compose_project"])
    lifecycle = str(state["lifecycle"])

    if lifecycle in INTERRUPTED_LIFECYCLES or lifecycle == "building":
        return _interrupted_result(action="stop", slug=slug, lifecycle=lifecycle, command="lab setup")

    argv_prefix = compose_argv_from_state(
        ctx.repo_root, lab_dir=lab_dir, state=state, subcommand=[]
    )
    if lifecycle == "stopped" or not compose_running(ctx, argv_prefix):
        write_state(
            ctx.repo_root,
            build_state_payload(
                slug=slug,
                compose_project=project,
                host_port=int(state["host_port"]),
                lifecycle="stopped",
                compose_file=str(state["compose_file"]),
                container_port=int(state["container_port"]),
            ),
        )
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={"action": "stop", "lab": slug, "project": project, "lifecycle": "stopped", "no_op": True},
            human_lines=[f"lab {slug} already stopped"],
            meta={"reset_safe": True},
        )

    try:
        with lab_lock(ctx.repo_root, slug):
            stop_argv = compose_argv_from_state(
                ctx.repo_root, lab_dir=lab_dir, state=state, subcommand=["stop"]
            )
            code, detail = run_compose(ctx, stop_argv, timeout=120.0)
            if code != 0 and not ctx.interrupted:
                return CliResult(
                    command="lab",
                    ok=False,
                    exit_code=1,
                    data={"action": "stop", "lab": slug, "detail": detail},
                    diagnostics=[Diagnostic("lifecycle.cli.internal", "compose stop failed")],
                    human_lines=["compose stop failed"],
                )
            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=int(state["host_port"]),
                    lifecycle="stopped",
                    compose_file=str(state["compose_file"]),
                    container_port=int(state["container_port"]),
                ),
            )
    except LabLockError as exc:
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "stop", "lab": slug},
            diagnostics=[Diagnostic("lifecycle.cli.internal", str(exc))],
            human_lines=[str(exc)],
        )

    if ctx.interrupted:
        return _interrupted_result(action="stop", slug=slug, lifecycle="stopped", command="lab stop")

    return CliResult(
        command="lab",
        ok=True,
        exit_code=0,
        data={"action": "stop", "lab": slug, "project": project, "lifecycle": "stopped"},
        human_lines=[f"lab {slug} stopped"],
        meta={"reset_safe": True},
    )


def handle_lab_reset(ctx: CliContext, args: list[str]) -> CliResult:
    selector, remove_volumes, confirm = _split_reset_args(args)
    resolved = _resolve(ctx, selector)
    if isinstance(resolved, CliResult):
        return resolved
    blocked = _mutation_blockers(resolved, action="reset")
    if blocked:
        return blocked
    slug = resolved.entry["slug"]
    lab_dir = resolved.lab_dir
    state = load_state(ctx.repo_root, slug)
    project = _project_for_dry_run(ctx, slug, state)

    down_cmd = ["down", "--remove-orphans"]
    if remove_volumes:
        down_cmd.append("--volumes")
    planned = [planned_compose_step(down_cmd)]
    if remove_volumes:
        planned.insert(0, "confirm destructive volume removal (--yes required without prompt)")

    if ctx.dry_run:
        lab_field = selector if selector.startswith("labs/") else slug
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "reset",
                "lab": lab_field,
                "project": project,
                "planned": planned,
            },
            human_lines=["lab reset dry-run: no containers or volumes changed"],
            meta={"reset_safe": True},
        )

    if remove_volumes and ctx.non_interactive and not confirm:
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "reset", "lab": slug, "destructive": True},
            diagnostics=[
                Diagnostic(
                    "lifecycle.interaction.non_interactive_required",
                    "lab reset --volumes requires --yes in non-interactive mode",
                )
            ],
            human_lines=["lab reset --volumes requires --yes in non-interactive mode"],
        )

    required = _require_state("reset", slug, state)
    if isinstance(required, CliResult):
        return required
    state = required
    project = str(state["compose_project"])
    lifecycle = str(state["lifecycle"])

    if lifecycle in INTERRUPTED_LIFECYCLES or lifecycle == "building":
        return _interrupted_result(action="reset", slug=slug, lifecycle=lifecycle, command="lab setup")

    argv_prefix = compose_argv_from_state(
        ctx.repo_root, lab_dir=lab_dir, state=state, subcommand=[]
    )
    if not compose_running(ctx, argv_prefix):
        write_state(
            ctx.repo_root,
            build_state_payload(
                slug=slug,
                compose_project=project,
                host_port=int(state["host_port"]),
                lifecycle="configured",
                compose_file=str(state["compose_file"]),
                container_port=int(state["container_port"]),
            ),
        )
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "reset",
                "lab": slug,
                "project": project,
                "lifecycle": "configured",
                "no_op": True,
                "evidence": "compose project already absent",
            },
            human_lines=[f"lab {slug} reset no-op; namespaced resources already absent"],
            meta={"reset_safe": True},
        )

    try:
        with lab_lock(ctx.repo_root, slug):
            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=int(state["host_port"]),
                    lifecycle="resetting",
                    compose_file=str(state["compose_file"]),
                    container_port=int(state["container_port"]),
                ),
            )
            down_argv = compose_argv_from_state(
                ctx.repo_root, lab_dir=lab_dir, state=state, subcommand=down_cmd
            )
            code, detail = run_compose(ctx, down_argv, timeout=300.0)
            if code != 0 and not ctx.interrupted:
                write_state(
                    ctx.repo_root,
                    build_state_payload(
                        slug=slug,
                        compose_project=project,
                        host_port=int(state["host_port"]),
                        lifecycle="failed",
                        compose_file=str(state["compose_file"]),
                        container_port=int(state["container_port"]),
                    ),
                )
                return CliResult(
                    command="lab",
                    ok=False,
                    exit_code=1,
                    data={"action": "reset", "lab": slug, "detail": detail},
                    diagnostics=[Diagnostic("lifecycle.cli.internal", "compose down failed during lab reset")],
                    human_lines=["compose down failed during lab reset"],
                )
            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=int(state["host_port"]),
                    lifecycle="configured",
                    compose_file=str(state["compose_file"]),
                    container_port=int(state["container_port"]),
                ),
            )
    except LabLockError as exc:
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "reset", "lab": slug},
            diagnostics=[Diagnostic("lifecycle.cli.internal", str(exc))],
            human_lines=[str(exc)],
        )

    if ctx.interrupted:
        return _interrupted_result(action="reset", slug=slug, lifecycle="resetting", command="lab reset")

    return CliResult(
        command="lab",
        ok=True,
        exit_code=0,
        data={"action": "reset", "lab": slug, "project": project, "lifecycle": "configured"},
        human_lines=[f"lab {slug} reset complete; configuration retained for lab start"],
        meta={"reset_safe": True},
    )
