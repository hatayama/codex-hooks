#!/usr/bin/env python3

import argparse
import shutil
import stat
from pathlib import Path

from codex_hooks.constants import (
    APP_NAME,
    BIN_FILES,
    BIN_INSTALL_DIR,
    INSTALL_ROOT,
    MANAGED_DIR_NAMES,
    ROOT_FILES,
    UNINSTALL_BLOCK,
    UNINSTALL_COMMENT,
    WRAPPER_BLOCK,
    WRAPPER_COMMENT,
)


def parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Codex Hooks installer")
    parser.add_argument(
        "--source-dir",
        default=str(Path(__file__).resolve().parent),
        help="Directory containing the project files",
    )
    return parser.parse_args()


def copy_tree(source_dir: Path, destination_dir: Path) -> None:
    shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)


def copy_file(source_path: Path, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_runtime_files(source_dir: Path) -> None:
    INSTALL_ROOT.mkdir(parents=True, exist_ok=True)

    for dir_name in MANAGED_DIR_NAMES:
        copy_tree(source_dir / dir_name, INSTALL_ROOT / dir_name)
    for filename in ROOT_FILES:
        copy_file(source_dir / filename, INSTALL_ROOT / filename)

    for filename in BIN_FILES:
        make_executable(BIN_INSTALL_DIR / filename)
    for filename in ROOT_FILES:
        make_executable(INSTALL_ROOT / filename)

    print(f"Installed runtime files to {INSTALL_ROOT}")


def append_block_if_missing(profile_path: Path, marker: str, block: str) -> bool:
    if profile_path.exists():
        content: str = profile_path.read_text()
        if marker in content:
            return True
    elif profile_path.name != ".zshrc":
        return False

    with open(profile_path, "a") as file_handle:
        file_handle.write(f"\n{block}")
    print(f"Updated {profile_path}")
    return True


def setup_shell_profiles() -> None:
    home: Path = Path.home()
    updated: bool = False

    if append_block_if_missing(home / ".zshrc", WRAPPER_COMMENT, WRAPPER_BLOCK):
        updated = True
    if (home / ".bashrc").exists():
        append_block_if_missing(home / ".bashrc", WRAPPER_COMMENT, WRAPPER_BLOCK)
        updated = True
    if (home / ".bash_profile").exists():
        append_block_if_missing(home / ".bash_profile", WRAPPER_COMMENT, WRAPPER_BLOCK)
        updated = True

    append_block_if_missing(home / ".zshrc", UNINSTALL_COMMENT, UNINSTALL_BLOCK)

    if updated:
        return

    print("Could not detect a shell profile. Add this manually:")
    print(WRAPPER_BLOCK.rstrip())


def print_completion(source_dir: Path) -> None:
    print()
    print(f"{APP_NAME} installation complete.")
    print()
    print("Restart your shell or run:")
    print("  source ~/.zshrc")
    print()
    print("To update later:")
    print(f"  cd {source_dir} && python3 install.py")
    print()
    print("Configuration priority:")
    print("  1. ~/.codex/hooks.json")
    print("  2. ~/.claude/settings.json")


def main() -> None:
    args: argparse.Namespace = parse_args()
    source_dir: Path = Path(args.source_dir).resolve()

    install_runtime_files(source_dir)
    setup_shell_profiles()
    print_completion(source_dir)


if __name__ == "__main__":
    main()
