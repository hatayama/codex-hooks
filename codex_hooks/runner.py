import json
import subprocess
import sys
from dataclasses import dataclass

from codex_hooks.config import HookCommand, HookGroup, ResolvedHooksConfig


@dataclass(frozen=True)
class TriggeredEvent:
    event_name: str
    matcher: str
    session_path: str
    cwd: str
    turn_id: str
    assistant_message: str
    raw_event: dict


@dataclass(frozen=True)
class HookResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


def group_matches(group: HookGroup, matcher: str) -> bool:
    if group.matcher == "":
        return True
    return group.matcher == matcher


def build_stdin_payload(event: TriggeredEvent) -> str:
    payload: dict[str, object] = {
        "event_name": event.event_name,
        "matched_matcher": event.matcher,
        "session_path": event.session_path,
        "cwd": event.cwd,
        "turn_id": event.turn_id,
        "assistant_message": event.assistant_message,
        "raw_event": event.raw_event,
    }
    return json.dumps(payload)


def spawn_hook_process(hook: HookCommand) -> subprocess.Popen[str]:
    assert hook.type == "command", "Unsupported hook type"
    return subprocess.Popen(
        ["/bin/sh", "-lc", hook.command],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def run_group(group: HookGroup, stdin_payload: str) -> tuple[HookResult, ...]:
    processes: list[tuple[str, subprocess.Popen[str]]] = []
    for hook in group.hooks:
        processes.append((hook.command, spawn_hook_process(hook)))

    results: list[HookResult] = []
    for command, process in processes:
        stdout: str
        stderr: str
        stdout, stderr = process.communicate(stdin_payload)
        results.append(
            HookResult(
                command=command,
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        )

    return tuple(results)


def fire_hooks(config: ResolvedHooksConfig, event: TriggeredEvent) -> tuple[HookResult, ...]:
    groups: tuple[HookGroup, ...] = config.hooks.get(event.event_name, ())
    if not groups:
        return ()

    stdin_payload: str = build_stdin_payload(event)
    results: list[HookResult] = []
    for group in groups:
        if not group_matches(group, event.matcher):
            continue
        results.extend(run_group(group, stdin_payload))
    return tuple(results)


def report_failures(results: tuple[HookResult, ...]) -> None:
    for result in results:
        if result.exit_code == 0:
            continue
        print(f"[FAIL] {result.command} (exit: {result.exit_code})", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
