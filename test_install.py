import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestInstallScripts(unittest.TestCase):
    def test_install_and_uninstall_work_in_clean_home(self) -> None:
        repo_root: Path = Path(__file__).resolve().parent

        with tempfile.TemporaryDirectory() as temp_home:
            home_path: Path = Path(temp_home)
            env: dict[str, str] = dict(os.environ)
            env["HOME"] = str(home_path)

            install_result: subprocess.CompletedProcess[str] = subprocess.run(
                ["python3", "install.py", "--source-dir", str(repo_root)],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            install_root: Path = home_path / ".codex-hooks"
            zshrc_path: Path = home_path / ".zshrc"
            installed_wrapper_path: Path = install_root / "bin" / "codex_hooks.py"
            installed_uninstall_path: Path = install_root / "uninstall.py"

            self.assertTrue(install_root.exists())
            self.assertTrue(installed_wrapper_path.exists())
            self.assertTrue(installed_uninstall_path.exists())
            self.assertTrue(zshrc_path.exists())
            self.assertIn("installation complete", install_result.stdout.lower())
            self.assertIn("Codex Hooks - codex wrapper", zshrc_path.read_text())
            self.assertIn("Codex Hooks - uninstall command", zshrc_path.read_text())

            uninstall_result: subprocess.CompletedProcess[str] = subprocess.run(
                ["python3", "uninstall.py"],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertFalse(install_root.exists())
            self.assertIn("Uninstall complete.", uninstall_result.stdout)
            self.assertNotIn("Codex Hooks - codex wrapper", zshrc_path.read_text())
            self.assertNotIn("Codex Hooks - uninstall command", zshrc_path.read_text())


if __name__ == "__main__":
    unittest.main()
