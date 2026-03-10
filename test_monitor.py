import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from codex_hooks.config import ResolvedHooksConfig
from codex_hooks.monitor import JsonlFollower, MonitorState, discover_session_file


class TestMonitor(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sessions_dir: Path = Path(self.temp_dir.name)
        self.cwd: str = "/tmp/project"
        self.config = ResolvedHooksConfig(
            source_path=Path("/tmp/hooks.json"),
            source_kind="codex",
            hooks={},
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def iso(self, timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    def write_session_file(
        self,
        name: str,
        meta_timestamp: float,
        body_events: list[dict],
        modified_at: float,
    ) -> Path:
        path: Path = self.sessions_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        events: list[dict] = [
            {
                "type": "session_meta",
                "payload": {
                    "cwd": self.cwd,
                    "timestamp": self.iso(meta_timestamp),
                },
            },
            *body_events,
        ]
        path.write_text("".join(f"{json.dumps(event)}\n" for event in events))
        os.utime(path, (modified_at, modified_at))
        return path

    def test_prefers_new_session_file_over_resumed_file(self) -> None:
        launch_ts: float = 2_000.0
        self.write_session_file(
            "2026/03/07/resumed.jsonl",
            meta_timestamp=launch_ts - 600.0,
            body_events=[],
            modified_at=launch_ts + 1.0,
        )
        new_path: Path = self.write_session_file(
            "2026/03/07/new.jsonl",
            meta_timestamp=launch_ts + 2.0,
            body_events=[],
            modified_at=launch_ts + 2.0,
        )

        with patch("codex_hooks.monitor.SESSIONS_DIR", self.sessions_dir):
            match = discover_session_file(launch_ts, self.cwd)

        self.assertIsNotNone(match)
        self.assertEqual(match.path, new_path)

    def test_resume_offset_skips_old_events(self) -> None:
        launch_ts: float = 3_000.0
        path: Path = self.write_session_file(
            "2026/03/07/resumed.jsonl",
            meta_timestamp=launch_ts - 600.0,
            body_events=[
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": "turn-1",
                        "last_agent_message": "Finished old work.",
                    },
                }
            ],
            modified_at=launch_ts - 5.0,
        )

        with patch("codex_hooks.monitor.SESSIONS_DIR", self.sessions_dir):
            match = discover_session_file(launch_ts, self.cwd)

        self.assertIsNotNone(match)
        follower: JsonlFollower = JsonlFollower(match.path, offset=match.initial_offset)

        with open(path, "a") as file_handle:
            file_handle.write(
                json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "task_complete",
                            "turn_id": "turn-2",
                            "last_agent_message": "Finished new work.",
                        },
                    }
                )
            )
            file_handle.write("\n")

        state: MonitorState = MonitorState(self.config, self.cwd, str(path))
        with patch("codex_hooks.monitor.fire_hooks", return_value=()) as fire_mock, patch(
            "codex_hooks.monitor.report_failures"
        ):
            events: list[dict] = follower.read_events()
            for event in events:
                state.handle_event(event)

        self.assertEqual(len(events), 1)
        triggered_event = fire_mock.call_args.args[1]
        self.assertEqual(triggered_event.turn_id, "turn-2")
        self.assertEqual(triggered_event.matcher, "done")

    def test_task_complete_uses_question_matcher(self) -> None:
        state: MonitorState = MonitorState(self.config, self.cwd, "/tmp/session.jsonl")
        event: dict = {
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "turn_id": "turn-4",
                "last_agent_message": "Need your confirmation?",
            },
        }

        with patch("codex_hooks.monitor.fire_hooks", return_value=()) as fire_mock, patch(
            "codex_hooks.monitor.report_failures"
        ):
            state.handle_event(event)

        triggered_event = fire_mock.call_args.args[1]
        self.assertEqual(triggered_event.event_name, "TaskComplete")
        self.assertEqual(triggered_event.matcher, "ask")

    def test_task_complete_uses_question_matcher_for_options_with_recommendation(self) -> None:
        state: MonitorState = MonitorState(self.config, self.cwd, "/tmp/session.jsonl")
        event: dict = {
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "turn_id": "turn-6",
                "last_agent_message": "Choose one\n1) Continue with the patch\n2) Stop here\nI recommend 1.",
            },
        }

        with patch("codex_hooks.monitor.fire_hooks", return_value=()) as fire_mock, patch(
            "codex_hooks.monitor.report_failures"
        ):
            state.handle_event(event)

        triggered_event = fire_mock.call_args.args[1]
        self.assertEqual(triggered_event.event_name, "TaskComplete")
        self.assertEqual(triggered_event.matcher, "ask")

    def test_task_started_maps_to_task_started_event(self) -> None:
        state: MonitorState = MonitorState(self.config, self.cwd, "/tmp/session.jsonl")
        event: dict = {
            "type": "event_msg",
            "payload": {
                "type": "task_started",
                "turn_id": "turn-5",
            },
        }

        with patch("codex_hooks.monitor.fire_hooks", return_value=()) as fire_mock, patch(
            "codex_hooks.monitor.report_failures"
        ):
            state.handle_event(event)

        triggered_event = fire_mock.call_args.args[1]
        self.assertEqual(triggered_event.event_name, "TaskStarted")
        self.assertEqual(triggered_event.matcher, "")


if __name__ == "__main__":
    unittest.main()
