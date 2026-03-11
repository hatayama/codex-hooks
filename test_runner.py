import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from codex_hooks.config import HookCommand, HookGroup, ResolvedHooksConfig
from codex_hooks.runner import TriggeredEvent, fire_hooks, report_failures


class TestRunner(unittest.TestCase):
    def build_config(self, groups: tuple[HookGroup, ...]) -> ResolvedHooksConfig:
        return ResolvedHooksConfig(
            source_path=Path("/tmp/hooks.json"),
            source_kind="codex",
            hooks={"TaskComplete": groups},
        )

    def test_runs_shell_quoted_command(self) -> None:
        config = self.build_config(
            (
                HookGroup(
                    matcher="done",
                    source_hook_event_name="Stop",
                    hooks=(HookCommand(type="command", command="printf '%s' 'hello world'"),),
                ),
            )
        )
        event = TriggeredEvent(
            event_name="TaskComplete",
            matcher="done",
            session_path="/tmp/session.jsonl",
            session_id="session-1",
            cwd="/tmp",
            turn_id="turn-1",
            assistant_message="done",
            raw_event={"type": "event_msg"},
        )

        results = fire_hooks(config, event)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].stdout, "hello world")

    def test_passes_json_payload_to_stdin(self) -> None:
        config = self.build_config(
            (
                HookGroup(
                    matcher="ask",
                    source_hook_event_name="Notification",
                    hooks=(HookCommand(type="command", command="cat"),),
                ),
            )
        )
        event = TriggeredEvent(
            event_name="TaskComplete",
            matcher="ask",
            session_path="/tmp/session.jsonl",
            session_id="session-2",
            cwd="/tmp",
            turn_id="turn-2",
            assistant_message="Need confirmation?",
            raw_event={"type": "event_msg", "payload": {"type": "task_complete"}},
        )

        results = fire_hooks(config, event)
        payload: dict = json.loads(results[0].stdout)

        self.assertEqual(payload["hook_event_name"], "Notification")
        self.assertEqual(payload["transcript_path"], "/tmp/session.jsonl")
        self.assertEqual(payload["session_id"], "session-2")
        self.assertEqual(payload["message"], "Need confirmation?")
        self.assertNotIn("event_name", payload)
        self.assertNotIn("matched_matcher", payload)
        self.assertNotIn("assistant_message", payload)

    def test_stop_payload_uses_last_assistant_message_even_for_question_matcher(self) -> None:
        config = self.build_config(
            (
                HookGroup(
                    matcher="",
                    source_hook_event_name="Stop",
                    hooks=(HookCommand(type="command", command="cat"),),
                ),
            )
        )
        event = TriggeredEvent(
            event_name="TaskComplete",
            matcher="ask",
            session_path="/tmp/session.jsonl",
            session_id="session-9",
            cwd="/tmp",
            turn_id="turn-9",
            assistant_message="Need confirmation?",
            raw_event={"type": "event_msg", "payload": {"type": "task_complete"}},
        )

        results = fire_hooks(config, event)
        payload: dict = json.loads(results[0].stdout)

        self.assertEqual(payload["hook_event_name"], "Stop")
        self.assertEqual(payload["session_id"], "session-9")
        self.assertEqual(payload["last_assistant_message"], "Need confirmation?")
        self.assertNotIn("message", payload)

    def test_reports_failures_without_stopping_other_hooks(self) -> None:
        config = self.build_config(
            (
                HookGroup(
                    matcher="done",
                    source_hook_event_name="Stop",
                    hooks=(
                        HookCommand(type="command", command="exit 3"),
                        HookCommand(type="command", command="printf ok"),
                    ),
                ),
            )
        )
        event = TriggeredEvent(
            event_name="TaskComplete",
            matcher="done",
            session_path="/tmp/session.jsonl",
            session_id="session-3",
            cwd="/tmp",
            turn_id="turn-3",
            assistant_message="done",
            raw_event={"type": "event_msg"},
        )

        results = fire_hooks(config, event)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            report_failures(results)

        self.assertEqual([result.exit_code for result in results], [3, 0])
        self.assertIn("[FAIL] exit 3", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
