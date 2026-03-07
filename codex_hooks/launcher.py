import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

COMMAND_TOKENS: set[str] = {
    "app",
    "app-server",
    "apply",
    "cloud",
    "completion",
    "debug",
    "exec",
    "features",
    "fork",
    "help",
    "login",
    "logout",
    "mcp",
    "mcp-server",
    "resume",
    "review",
    "sandbox",
}
VALUE_OPTIONS: set[str] = {
    "-C",
    "--add-dir",
    "--ask-for-approval",
    "--cd",
    "--config",
    "--disable",
    "--enable",
    "--image",
    "--local-provider",
    "--model",
    "--profile",
    "--sandbox",
    "-a",
    "-c",
    "-i",
    "-m",
    "-p",
    "-s",
}


def resolve_codex_binary() -> str:
    binary_path: str | None = shutil.which("codex")
    if binary_path is None:
        return ""
    return binary_path


def resolve_target_cwd(args: list[str]) -> str:
    default_cwd: str = os.getcwd()
    for index, arg in enumerate(args):
        if arg == "-C" or arg == "--cd":
            if index + 1 < len(args):
                return str(Path(args[index + 1]).expanduser().resolve())
        if arg.startswith("--cd="):
            return str(Path(arg.split("=", 1)[1]).expanduser().resolve())
    return default_cwd


def resolve_codex_command(args: list[str]) -> str:
    skip_next: bool = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in VALUE_OPTIONS:
            skip_next = True
            continue
        if any(
            arg.startswith(prefix)
            for prefix in (
                "--add-dir=",
                "--ask-for-approval=",
                "--cd=",
                "--config=",
                "--disable=",
                "--enable=",
                "--image=",
                "--local-provider=",
                "--model=",
                "--profile=",
                "--sandbox=",
            )
        ):
            continue
        if arg.startswith("-"):
            continue
        if arg in COMMAND_TOKENS:
            return arg
        return ""
    return ""


def should_allow_resumed_fallback(args: list[str]) -> bool:
    command: str = resolve_codex_command(args)
    return command == "resume" or command == "fork"


def should_wrap() -> bool:
    return os.environ.get("CODEX_HOOKS_DISABLE") != "1"


def spawn_monitor(
    root_dir: Path,
    cwd: str,
    launch_ts: float,
    codex_pid: int,
    allow_resumed_fallback: bool,
) -> None:
    monitor_script: Path = root_dir / "bin" / "codex_hooks_monitor.py"
    command: list[str] = [
        sys.executable,
        str(monitor_script),
        "--cwd",
        cwd,
        "--launch-ts",
        str(launch_ts),
        "--codex-pid",
        str(codex_pid),
    ]
    if allow_resumed_fallback:
        command.append("--allow-resumed-fallback")

    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=None,
        start_new_session=True,
    )


def main() -> None:
    args: list[str] = sys.argv[1:]
    codex_binary: str = resolve_codex_binary()
    if not codex_binary:
        print("codex-hooks: codex binary not found", file=sys.stderr)
        raise SystemExit(127)

    if not should_wrap():
        completed: subprocess.CompletedProcess[bytes] = subprocess.run([codex_binary, *args])
        raise SystemExit(completed.returncode)

    target_cwd: str = resolve_target_cwd(args)
    launch_ts: float = time.time()
    root_dir: Path = Path(__file__).resolve().parent.parent
    allow_resumed_fallback: bool = should_allow_resumed_fallback(args)

    codex_process: subprocess.Popen[bytes] = subprocess.Popen([codex_binary, *args])
    spawn_monitor(
        root_dir=root_dir,
        cwd=target_cwd,
        launch_ts=launch_ts,
        codex_pid=codex_process.pid,
        allow_resumed_fallback=allow_resumed_fallback,
    )
    raise SystemExit(codex_process.wait())
