import unittest

from codex_hooks.status import completion_matcher, looks_like_question


class TestStatus(unittest.TestCase):
    def test_detects_question_mark(self) -> None:
        self.assertTrue(looks_like_question("Do you want me to continue?"))
        self.assertTrue(looks_like_question("この方針で進めますか？"))

    def test_detects_numbered_options(self) -> None:
        message: str = "Choose one:\n1. Continue with the patch\n2. Stop here"
        self.assertTrue(looks_like_question(message))

    def test_returns_done_for_plain_completion(self) -> None:
        self.assertEqual(completion_matcher("Finished the implementation."), "done")


if __name__ == "__main__":
    unittest.main()
