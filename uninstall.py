#!/usr/bin/env python3

import shutil
from pathlib import Path

from codex_hooks.constants import (
    APP_NAME,
    INSTALL_ROOT,
    UNINSTALL_COMMENT,
    UNINSTALL_FUNCTION_NAME,
    WRAPPER_COMMENT,
    WRAPPER_FUNCTION_NAME,
)


def remove_install_root() -> None:
    if not INSTALL_ROOT.exists():
        return
    shutil.rmtree(INSTALL_ROOT)
    print(f"Removed {INSTALL_ROOT}")


def remove_shell_block(profile_path: Path, marker: str, function_name: str) -> None:
    if not profile_path.exists():
        return

    content: str = profile_path.read_text()
    if marker not in content and function_name not in content:
        return

    lines: list[str] = content.splitlines(keepends=True)
    filtered: list[str] = []
    inside_block: bool = False

    for line in lines:
        if marker in line:
            inside_block = True
            continue
        if inside_block:
            if line.rstrip() == "}":
                inside_block = False
                continue
            continue
        filtered.append(line)

    profile_path.write_text("".join(filtered))
    print(f"Updated {profile_path}")


def clean_shell_profiles() -> None:
    home: Path = Path.home()
    for profile_path in (home / ".zshrc", home / ".bashrc", home / ".bash_profile"):
        remove_shell_block(profile_path, WRAPPER_COMMENT, WRAPPER_FUNCTION_NAME)
    remove_shell_block(home / ".zshrc", UNINSTALL_COMMENT, UNINSTALL_FUNCTION_NAME)


def main() -> None:
    print(f"{APP_NAME} uninstall")
    print()
    remove_install_root()
    clean_shell_profiles()
    print()
    print("Uninstall complete.")


if __name__ == "__main__":
    main()
