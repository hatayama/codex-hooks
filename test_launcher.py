import os
import unittest
from unittest.mock import patch

from codex_hooks.launcher import (
    resolve_target_cwd,
    should_allow_resumed_fallback,
    should_wrap,
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


if __name__ == "__main__":
    unittest.main()
