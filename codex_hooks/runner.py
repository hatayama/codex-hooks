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
    session_id: str
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


def default_hook_event_name(event: TriggeredEvent) -> str:
    if event.event_name == "TaskStarted":
        return "UserPromptSubmit"
    if event.event_name == "TurnAborted":
        return "Stop"
    if event.event_name == "TaskComplete" and event.matcher == "ask":
        return "Notification"
    if event.event_name == "TaskComplete":
        return "Stop"
    return event.event_name


def build_stdin_payload(event: TriggeredEvent, group: HookGroup) -> str:
    hook_event_name: str = group.source_hook_event_name or default_hook_event_name(event)
    payload: dict[str, object] = {
        "hook_event_name": hook_event_name,
        "transcript_path": event.session_path,
        "cwd": event.cwd,
        "session_id": event.session_id,
        "raw_event": event.raw_event,
    }
    if hook_event_name == "Notification":
        payload["message"] = event.assistant_message
    if hook_event_name == "Stop":
        payload["last_assistant_message"] = event.assistant_message
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

    results: list[HookResult] = []
    for group in groups:
        if not group_matches(group, event.matcher):
            continue
        stdin_payload: str = build_stdin_payload(event, group)
        results.extend(run_group(group, stdin_payload))
    return tuple(results)


def report_failures(results: tuple[HookResult, ...]) -> None:
    for result in results:
        if result.exit_code == 0:
            continue
        print(f"[FAIL] {result.command} (exit: {result.exit_code})", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
