import unittest

from codex_hooks.status import completion_matcher, looks_like_question


class TestStatus(unittest.TestCase):
    def test_detects_question_mark(self) -> None:
        self.assertTrue(looks_like_question("Do you want me to continue?"))
        self.assertTrue(looks_like_question("この方針で進めますか？"))

    def test_detects_numbered_options_with_colon(self) -> None:
        message: str = "Choose one:\n1. Continue with the patch\n2. Stop here"
        self.assertTrue(looks_like_question(message))

    def test_detects_numbered_options_without_colon(self) -> None:
        message: str = "Choose one\n1. Continue with the patch\n2. Stop here"
        self.assertTrue(looks_like_question(message))

    def test_detects_parenthesized_numbered_options(self) -> None:
        message: str = "Choose one:\n1) Continue with the patch\n2) Stop here"
        self.assertTrue(looks_like_question(message))

    def test_detects_bulleted_options(self) -> None:
        message: str = "Options:\n- Continue with the patch\n- Stop here"
        self.assertTrue(looks_like_question(message))

    def test_detects_japanese_options(self) -> None:
        message: str = "次から選んでください：\n1. 続ける\n2. 止める"
        self.assertTrue(looks_like_question(message))

    def test_detects_options_with_trailing_recommendation(self) -> None:
        message: str = "Choose one:\n1. Continue with the patch\n2. Stop here\nI recommend 1."
        self.assertTrue(looks_like_question(message))

    def test_detects_bulleted_options_with_trailing_recommendation(self) -> None:
        message: str = "次から選んでください\n- 続ける\n- 止める\nおすすめは 2 です。"
        self.assertTrue(looks_like_question(message))

    def test_ignores_summary_heading_with_bulleted_completion(self) -> None:
        message: str = "Summary:\n- fixed A\n- added B"
        self.assertFalse(looks_like_question(message))

    def test_ignores_plain_bulleted_completion(self) -> None:
        message: str = "- Implemented A\n- Added B"
        self.assertFalse(looks_like_question(message))

    def test_rejects_options_followed_by_plain_statement(self) -> None:
        message: str = "Options:\n- A\n- B\nImplemented A."
        self.assertFalse(looks_like_question(message))

    def test_rejects_numbered_options_followed_by_thanks(self) -> None:
        message: str = "Choose one:\n1) A\n2) B\nThanks!"
        self.assertFalse(looks_like_question(message))

    def test_returns_done_for_plain_completion(self) -> None:
        self.assertEqual(completion_matcher("Finished the implementation."), "done")


if __name__ == "__main__":
    unittest.main()
