import json
import tempfile
import unittest
from pathlib import Path

from codex_hooks.config import load_hooks_config


class TestConfig(unittest.TestCase):
    def test_prefers_codex_hooks_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root: Path = Path(temp_dir)
            codex_path: Path = root / "hooks.json"
            claude_path: Path = root / "settings.json"

            codex_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "TaskComplete": [
                                {
                                    "matcher": "done",
                                    "hooks": [
                                        {"type": "command", "command": "printf codex"}
                                    ],
                                }
                            ]
                        }
                    }
                )
            )
            claude_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "Stop": [
                                {
                                    "matcher": "",
                                    "hooks": [
                                        {"type": "command", "command": "printf claude"}
                                    ],
                                }
                            ]
                        }
                    }
                )
            )

            config = load_hooks_config(codex_hooks_path=codex_path, claude_settings_path=claude_path)

        self.assertEqual(config.source_kind, "codex")
        self.assertIn("TaskComplete", config.hooks)
        self.assertNotIn("TurnAborted", config.hooks)
        self.assertEqual(config.hooks["TaskComplete"][0].hooks[0].command, "printf codex")

    def test_maps_claude_hooks_to_task_started_complete_and_abort(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root: Path = Path(temp_dir)
            codex_path: Path = root / "missing-hooks.json"
            claude_path: Path = root / "settings.json"

            claude_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "UserPromptSubmit": [
                                {
                                    "matcher": "",
                                    "hooks": [
                                        {"type": "command", "command": "printf on"}
                                    ],
                                }
                            ],
                            "PreToolUse": [
                                {
                                    "matcher": "",
                                    "hooks": [
                                        {"type": "command", "command": "printf on"}
                                    ],
                                }
                            ],
                            "Stop": [
                                {
                                    "matcher": "",
                                    "hooks": [
                                        {"type": "command", "command": "printf stop"}
                                    ],
                                }
                            ],
                            "Notification": [
                                {
                                    "matcher": "permission_prompt",
                                    "hooks": [
                                        {"type": "command", "command": "printf notify"}
                                    ],
                                }
                            ],
                        }
                    }
                )
            )

            config = load_hooks_config(codex_hooks_path=codex_path, claude_settings_path=claude_path)

        self.assertEqual(config.source_kind, "claude")
        self.assertEqual(len(config.hooks["TaskStarted"]), 1)
        self.assertEqual(config.hooks["TaskStarted"][0].hooks[0].command, "printf on")
        self.assertEqual(len(config.hooks["TaskComplete"]), 2)
        self.assertEqual(config.hooks["TaskComplete"][0].matcher, "")
        self.assertEqual(config.hooks["TaskComplete"][1].matcher, "ask")
        self.assertEqual(config.hooks["TurnAborted"][0].matcher, "")


if __name__ == "__main__":
    unittest.main()
