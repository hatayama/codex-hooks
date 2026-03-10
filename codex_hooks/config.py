import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codex_hooks.constants import (
    DEFAULT_CLAUDE_SETTINGS_PATH,
    DEFAULT_CODEX_HOOKS_PATH,
    SUPPORTED_CODEX_EVENTS,
)


@dataclass(frozen=True)
class HookCommand:
    type: str
    command: str


@dataclass(frozen=True)
class HookGroup:
    matcher: str
    hooks: tuple[HookCommand, ...]
    source_hook_event_name: str = ""

    def with_matcher(self, matcher: str) -> "HookGroup":
        return HookGroup(
            matcher=matcher,
            hooks=self.hooks,
            source_hook_event_name=self.source_hook_event_name,
        )


@dataclass(frozen=True)
class ResolvedHooksConfig:
    source_path: Path
    source_kind: str
    hooks: dict[str, tuple[HookGroup, ...]]


def load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def parse_command(data: dict[str, Any]) -> HookCommand:
    command_type: Any = data.get("type")
    command: Any = data.get("command")
    assert command_type == "command", "Only command hooks are supported"
    assert isinstance(command, str) and command != "", "Hook command must be a non-empty string"
    return HookCommand(type="command", command=command)


def parse_group(data: dict[str, Any], source_hook_event_name: str = "") -> HookGroup:
    matcher: Any = data.get("matcher", "")
    hooks_data: Any = data.get("hooks")
    assert isinstance(matcher, str), "Hook matcher must be a string"
    assert isinstance(hooks_data, list), "Hook group must contain a hooks list"
    hooks: tuple[HookCommand, ...] = tuple(parse_command(item) for item in hooks_data)
    return HookGroup(
        matcher=matcher,
        hooks=hooks,
        source_hook_event_name=source_hook_event_name,
    )


def parse_hooks_section(
    raw_hooks: dict[str, Any],
    preserve_source_event_name: bool = False,
) -> dict[str, tuple[HookGroup, ...]]:
    parsed: dict[str, tuple[HookGroup, ...]] = {}
    for event_name, groups_data in raw_hooks.items():
        assert isinstance(event_name, str), "Hook event name must be a string"
        assert isinstance(groups_data, list), "Hook event value must be a list"
        source_hook_event_name: str = event_name if preserve_source_event_name else ""
        parsed[event_name] = tuple(
            parse_group(item, source_hook_event_name=source_hook_event_name)
            for item in groups_data
        )
    return parsed


def extend_unique_groups(destination: list[HookGroup], groups: tuple[HookGroup, ...]) -> None:
    for group in groups:
        if any(
            existing.matcher == group.matcher and existing.hooks == group.hooks
            for existing in destination
        ):
            continue
        destination.append(group)


def map_claude_hooks(raw_hooks: dict[str, Any]) -> dict[str, tuple[HookGroup, ...]]:
    parsed: dict[str, tuple[HookGroup, ...]] = parse_hooks_section(
        raw_hooks,
        preserve_source_event_name=True,
    )
    mapped: dict[str, list[HookGroup]] = {
        event_name: [] for event_name in SUPPORTED_CODEX_EVENTS
    }

    user_prompt_submit_groups: tuple[HookGroup, ...] = parsed.get("UserPromptSubmit", ())
    pre_tool_use_groups: tuple[HookGroup, ...] = parsed.get("PreToolUse", ())
    stop_groups: tuple[HookGroup, ...] = parsed.get("Stop", ())
    notification_groups: tuple[HookGroup, ...] = parsed.get("Notification", ())

    extend_unique_groups(mapped["TaskStarted"], user_prompt_submit_groups)
    extend_unique_groups(mapped["TaskStarted"], pre_tool_use_groups)
    extend_unique_groups(mapped["TaskComplete"], stop_groups)
    extend_unique_groups(mapped["TurnAborted"], stop_groups)
    extend_unique_groups(
        mapped["TaskComplete"],
        tuple(group.with_matcher("ask") for group in notification_groups),
    )

    return {
        event_name: tuple(groups)
        for event_name, groups in mapped.items()
        if groups
    }


def load_codex_hooks(path: Path) -> ResolvedHooksConfig:
    raw: dict[str, Any] = load_json_file(path)
    hooks_data: Any = raw.get("hooks")
    assert isinstance(hooks_data, dict), "codex hooks config must contain a hooks object"
    parsed: dict[str, tuple[HookGroup, ...]] = parse_hooks_section(hooks_data)
    return ResolvedHooksConfig(source_path=path, source_kind="codex", hooks=parsed)


def load_claude_hooks(path: Path) -> ResolvedHooksConfig:
    raw: dict[str, Any] = load_json_file(path)
    hooks_data: Any = raw.get("hooks")
    assert isinstance(hooks_data, dict), "Claude settings must contain a hooks object"
    parsed: dict[str, tuple[HookGroup, ...]] = map_claude_hooks(hooks_data)
    return ResolvedHooksConfig(source_path=path, source_kind="claude", hooks=parsed)


def load_hooks_config(
    codex_hooks_path: Path = DEFAULT_CODEX_HOOKS_PATH,
    claude_settings_path: Path = DEFAULT_CLAUDE_SETTINGS_PATH,
) -> ResolvedHooksConfig:
    if codex_hooks_path.exists():
        return load_codex_hooks(codex_hooks_path)
    return load_claude_hooks(claude_settings_path)
