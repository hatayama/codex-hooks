import os
import unittest
from unittest.mock import Mock, patch

from codex_hooks.launcher import (
    resolve_target_cwd,
    should_allow_resumed_fallback,
    should_wrap,
    wait_for_exit_without_interrupt_traceback,
)


class TestLauncher(unittest.TestCase):
    def test_resolve_target_cwd_from_cd_option(self) -> None:
        cwd: str = resolve_target_cwd(["--cd", "~/tmp"])
        self.assertTrue(cwd.endswith("/tmp"))

    def test_resume_and_fork_allow_resumed_fallback(self) -> None:
        self.assertTrue(should_allow_resumed_fallback(["resume", "abc123"]))
        self.assertTrue(should_allow_resumed_fallback(["fork", "abc123"]))
        self.assertFalse(should_allow_resumed_fallback(["review"]))

    def test_disable_env_bypasses_wrapper(self) -> None:
        with patch.dict(os.environ, {"CODEX_HOOKS_DISABLE": "1"}, clear=False):
            self.assertFalse(should_wrap())

    def test_wait_for_exit_without_interrupt_traceback_returns_process_code(self) -> None:
        codex_process: Mock = Mock()
        codex_process.wait.return_value = 0

        exit_code: int = wait_for_exit_without_interrupt_traceback(codex_process)

        self.assertEqual(0, exit_code)

    def test_wait_for_exit_without_interrupt_traceback_returns_polled_code_after_interrupt(self) -> None:
        codex_process: Mock = Mock()
        codex_process.wait.side_effect = KeyboardInterrupt()
        codex_process.poll.return_value = 130

        exit_code: int = wait_for_exit_without_interrupt_traceback(codex_process)

        self.assertEqual(130, exit_code)

    def test_wait_for_exit_without_interrupt_traceback_retries_until_process_exits(self) -> None:
        codex_process: Mock = Mock()
        codex_process.wait.side_effect = [KeyboardInterrupt(), 0]
        codex_process.poll.return_value = None

        exit_code: int = wait_for_exit_without_interrupt_traceback(codex_process)

        self.assertEqual(0, exit_code)


if __name__ == "__main__":
    unittest.main()
