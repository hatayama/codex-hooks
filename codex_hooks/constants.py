from pathlib import Path

APP_NAME: str = "Codex Hooks"
INSTALL_ROOT: Path = Path.home() / ".codex-hooks"
BIN_INSTALL_DIR: Path = INSTALL_ROOT / "bin"
PACKAGE_INSTALL_DIR: Path = INSTALL_ROOT / "codex_hooks"

BIN_FILES: list[str] = ["codex_hooks.py", "codex_hooks_monitor.py"]
ROOT_FILES: list[str] = ["uninstall.py"]
MANAGED_DIR_NAMES: list[str] = ["bin", "codex_hooks"]

SESSIONS_DIR: Path = Path.home() / ".codex" / "sessions"
DEFAULT_CODEX_HOOKS_PATH: Path = Path.home() / ".codex" / "hooks.json"
DEFAULT_CLAUDE_SETTINGS_PATH: Path = Path.home() / ".claude" / "settings.json"

SUPPORTED_CODEX_EVENTS: tuple[str, str, str] = (
    "TaskStarted",
    "TaskComplete",
    "TurnAborted",
)

POLL_INTERVAL_SEC: float = 0.25
SESSION_DISCOVERY_TIMEOUT_SEC: float = 30.0
EXIT_GRACE_SEC: float = 3.0
DISCOVERY_SKEW_SEC: float = 5.0

WRAPPER_COMMENT: str = "# Codex Hooks - codex wrapper"
WRAPPER_FUNCTION_NAME: str = "codex"
WRAPPER_BLOCK: str = (
    f"{WRAPPER_COMMENT}\n"
    "codex() {\n"
    '  if [ "${CODEX_HOOKS_DISABLE:-0}" = "1" ]; then\n'
    '    command codex "$@"\n'
    "    return $?\n"
    "  fi\n"
    '  python3 "$HOME/.codex-hooks/bin/codex_hooks.py" "$@"\n'
    "}\n"
)

UNINSTALL_COMMENT: str = "# Codex Hooks - uninstall command"
UNINSTALL_FUNCTION_NAME: str = "uninstall_codex_hooks"
UNINSTALL_BLOCK: str = (
    f"{UNINSTALL_COMMENT}\n"
    "uninstall_codex_hooks() {\n"
    '  python3 "$HOME/.codex-hooks/uninstall.py"\n'
    "}\n"
)
