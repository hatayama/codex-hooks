import argparse
import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from codex_hooks.config import ResolvedHooksConfig, load_hooks_config
from codex_hooks.constants import (
    DISCOVERY_SKEW_SEC,
    EXIT_GRACE_SEC,
    POLL_INTERVAL_SEC,
    SESSION_DISCOVERY_TIMEOUT_SEC,
    SESSIONS_DIR,
)
from codex_hooks.runner import TriggeredEvent, fire_hooks, report_failures
from codex_hooks.status import completion_matcher, extract_output_text


def parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Codex Hooks session monitor")
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--launch-ts", required=True, type=float)
    parser.add_argument("--codex-pid", required=True, type=int)
    parser.add_argument("--allow-resumed-fallback", action="store_true")
    return parser.parse_args()


def iso_to_timestamp(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def paths_match(left: str, right: str) -> bool:
    return Path(left).resolve() == Path(right).resolve()


def pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    completed: subprocess.CompletedProcess[bytes] = subprocess.run(
        ["ps", "-p", str(pid)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def load_session_meta(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as file_handle:
        first_line: str = file_handle.readline().strip()
    if not first_line:
        return None
    data: dict = json.loads(first_line)
    if data.get("type") != "session_meta":
        return None
    payload: object = data.get("payload", {})
    assert isinstance(payload, dict), "session_meta payload must be an object"
    return payload


@dataclass(frozen=True)
class SessionFileMatch:
    path: Path
    initial_offset: int
    meta_ts: float
    last_modified_ts: float
    was_created_after_launch: bool


def build_session_match(path: Path, launch_ts: float, cwd: str) -> SessionFileMatch | None:
    meta: dict | None = load_session_meta(path)
    if meta is None:
        return None

    meta_cwd: str = meta.get("cwd", "")
    if not meta_cwd or not paths_match(meta_cwd, cwd):
        return None

    timestamp: str = meta.get("timestamp", "")
    if not timestamp:
        return None

    meta_ts: float = iso_to_timestamp(timestamp)
    stat_result = path.stat()
    was_created_after_launch: bool = meta_ts >= launch_ts - DISCOVERY_SKEW_SEC
    initial_offset: int = 0
    if not was_created_after_launch:
        initial_offset = stat_result.st_size

    return SessionFileMatch(
        path=path,
        initial_offset=initial_offset,
        meta_ts=meta_ts,
        last_modified_ts=stat_result.st_mtime,
        was_created_after_launch=was_created_after_launch,
    )


def discover_session_file(
    launch_ts: float,
    cwd: str,
    allow_resumed_fallback: bool = True,
) -> SessionFileMatch | None:
    if not SESSIONS_DIR.exists():
        return None

    candidates: list[SessionFileMatch] = []
    for path in SESSIONS_DIR.rglob("*.jsonl"):
        match: SessionFileMatch | None = build_session_match(path, launch_ts, cwd)
        if match is None:
            continue
        if not allow_resumed_fallback and not match.was_created_after_launch:
            continue
        candidates.append(match)

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (item.was_created_after_launch, item.last_modified_ts, item.meta_ts),
        reverse=True,
    )
    return candidates[0]


@dataclass
class JsonlFollower:
    path: Path
    offset: int = 0
    pending: str = ""

    def read_events(self) -> list[dict]:
        if not self.path.exists():
            return []

        with open(self.path) as file_handle:
            file_handle.seek(self.offset)
            chunk: str = file_handle.read()
            self.offset = file_handle.tell()

        if not chunk:
            return []

        data: str = self.pending + chunk
        lines: list[str] = data.splitlines(keepends=True)
        self.pending = ""
        events: list[dict] = []

        for line in lines:
            if not line.endswith("\n"):
                self.pending = line
                continue
            stripped: str = line.strip()
            if not stripped:
                continue
            events.append(json.loads(stripped))

        return events


@dataclass
class MonitorState:
    config: ResolvedHooksConfig
    cwd: str
    session_path: str
    last_assistant_message: str = ""
    last_event_at: float = 0.0
    seen_terminal_events: set[tuple[str, str]] = field(default_factory=set)

    def remember_assistant_message(self, payload: dict) -> None:
        payload_type: str = payload.get("type", "")
        if payload_type != "message":
            return
        if payload.get("role") != "assistant":
            return
        message_text: str = extract_output_text(payload)
        if not message_text:
            return
        self.last_assistant_message = message_text

    def build_triggered_event(self, event: dict) -> TriggeredEvent | None:
        event_type: str = event.get("type", "")
        payload: dict = event.get("payload", {})
        self.last_event_at = time.time()

        if event_type == "response_item":
            self.remember_assistant_message(payload)
            return None

        if event_type != "event_msg":
            return None

        payload_type: str = payload.get("type", "")
        turn_id: str = payload.get("turn_id", "")
        if payload_type == "task_started":
            return TriggeredEvent(
                event_name="TaskStarted",
                matcher="",
                session_path=self.session_path,
                cwd=self.cwd,
                turn_id=turn_id,
                assistant_message="",
                raw_event=event,
            )

        if payload_type == "turn_aborted":
            return TriggeredEvent(
                event_name="TurnAborted",
                matcher="aborted",
                session_path=self.session_path,
                cwd=self.cwd,
                turn_id=turn_id,
                assistant_message="",
                raw_event=event,
            )

        if payload_type != "task_complete":
            return None

        message: str = (payload.get("last_agent_message") or self.last_assistant_message).strip()
        matcher: str = completion_matcher(message)
        return TriggeredEvent(
            event_name="TaskComplete",
            matcher=matcher,
            session_path=self.session_path,
            cwd=self.cwd,
            turn_id=turn_id,
            assistant_message=message,
            raw_event=event,
        )

    def should_skip(self, event: TriggeredEvent) -> bool:
        if event.event_name not in {"TaskComplete", "TurnAborted"}:
            return False
        if not event.turn_id:
            return False
        event_key: tuple[str, str] = (event.event_name, event.turn_id)
        if event_key in self.seen_terminal_events:
            return True
        self.seen_terminal_events.add(event_key)
        return False

    def handle_event(self, event: dict) -> None:
        triggered_event: TriggeredEvent | None = self.build_triggered_event(event)
        if triggered_event is None:
            return
        if self.should_skip(triggered_event):
            return
        results = fire_hooks(self.config, triggered_event)
        report_failures(results)


def main() -> None:
    args: argparse.Namespace = parse_args()
    config: ResolvedHooksConfig = load_hooks_config()
    follower: JsonlFollower | None = None
    state: MonitorState | None = None
    discovery_deadline: float = args.launch_ts + SESSION_DISCOVERY_TIMEOUT_SEC
    last_event_at: float = args.launch_ts

    while True:
        codex_alive: bool = pid_is_alive(args.codex_pid)

        if follower is None:
            match: SessionFileMatch | None = discover_session_file(
                args.launch_ts,
                args.cwd,
                allow_resumed_fallback=args.allow_resumed_fallback,
            )
            if match is not None:
                follower = JsonlFollower(match.path, offset=match.initial_offset)
                state = MonitorState(
                    config=config,
                    cwd=args.cwd,
                    session_path=str(match.path),
                    last_event_at=args.launch_ts,
                )
                continue
            if not codex_alive or time.time() > discovery_deadline:
                break
            time.sleep(POLL_INTERVAL_SEC)
            continue

        events: list[dict] = follower.read_events()
        if state is not None:
            for event in events:
                state.handle_event(event)
            last_event_at = state.last_event_at

        if codex_alive:
            time.sleep(POLL_INTERVAL_SEC)
            continue

        if time.time() - last_event_at > EXIT_GRACE_SEC:
            break
        time.sleep(POLL_INTERVAL_SEC)
