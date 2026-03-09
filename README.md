# codex-hooks

`codex-hooks` is a macOS-focused Python tool that replays a compatible subset of Claude-style command hooks for Codex by watching Codex session JSONL files.

This repository intentionally stays focused on hook reproduction. It does not own UI features such as desktop notifications or terminal title updates. Its job is only to decide when hooks should fire and which commands should run.

## Current Compatibility

`codex-hooks` currently supports a compatible subset of Claude-style command hooks.

What works today:

- Reading `~/.codex/hooks.json`
- Falling back to `~/.claude/settings.json`
- Watching Codex session JSONL files
- Firing command hooks for `TaskStarted`, `TaskComplete`, and `TurnAborted`
- Reusing Claude hooks that only need shell execution plus stdin input

This works well for hooks such as:

- Desktop notifications
- Terminal or iTerm title updates
- Sound effects
- Shell scripts that perform direct side effects

What does not work today:

- Claude's full hook response protocol
- Hook stdout such as `{"decision":"block","reason":"..."}`
- Hooks that expect Claude to load a Skill automatically
- Hooks that depend on Claude-specific stdin fields
- Full Claude matcher and lifecycle compatibility

## Install

```sh
git clone https://github.com/hatayama/codex-hooks.git
cd codex-hooks
python3 install.py
source ~/.zshrc
```

After installation, a `codex` shell function is added. It launches the real Codex CLI and starts a background session monitor at the same time.

To disable the wrapper temporarily:

```sh
CODEX_HOOKS_DISABLE=1 codex ...
```

## Configuration Priority

1. `~/.codex/hooks.json`
2. `~/.claude/settings.json`

If `~/.codex/hooks.json` exists, it takes precedence. Otherwise, `codex-hooks` falls back to Claude's `settings.json`.

## Example `~/.codex/hooks.json`

Create `~/.codex/hooks.json` like this:

This example only uses built-in macOS commands so it works without any custom scripts:

```sh
mkdir -p ~/.codex
cat > ~/.codex/hooks.json <<'EOF'
{
  "hooks": {
    "TaskStarted": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'beep 1'"
          }
        ]
      }
    ],
    "TaskComplete": [
      {
        "matcher": "done",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Codex finished.\" with title \"codex-hooks\" sound name \"Glass\"'"
          }
        ]
      },
      {
        "matcher": "ask",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Codex is waiting for your reply.\" with title \"codex-hooks\" sound name \"Hero\"'"
          }
        ]
      }
    ],
    "TurnAborted": [
      {
        "matcher": "aborted",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"The Codex turn was aborted.\" with title \"codex-hooks\" sound name \"Basso\"'"
          }
        ]
      }
    ]
  }
}
EOF
```

The file uses the same `hooks` structure as Claude:

```json
{
  "hooks": {
    "TaskStarted": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'beep 1'"
          }
        ]
      }
    ],
    "TaskComplete": [
      {
        "matcher": "done",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Codex finished.\" with title \"codex-hooks\" sound name \"Glass\"'"
          }
        ]
      },
      {
        "matcher": "ask",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Codex is waiting for your reply.\" with title \"codex-hooks\" sound name \"Hero\"'"
          }
        ]
      }
    ],
    "TurnAborted": [
      {
        "matcher": "aborted",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"The Codex turn was aborted.\" with title \"codex-hooks\" sound name \"Basso\"'"
          }
        ]
      }
    ]
  }
}
```

## Events and Matchers

### `TaskStarted`

- Source: `event_msg.payload.type == "task_started"`
- Supported matcher: `""`

### `TaskComplete`

- Source: `event_msg.payload.type == "task_complete"`
- Supported matcher: `""`, `done`, `ask`
- `ask` is used when the final assistant message ends with a question or numbered options

### `TurnAborted`

- Source: `event_msg.payload.type == "turn_aborted"`
- Supported matcher: `""`, `aborted`

## Claude Fallback Mapping

When `~/.claude/settings.json` is used as the source, Claude events are mapped onto Codex events like this:

- `UserPromptSubmit` and `PreToolUse` hooks run on:
  - `TaskStarted`
- `Stop` hooks run on:
  - `TaskComplete`
  - `TurnAborted`
- `Notification` hooks run on:
  - `TaskComplete` with the `ask` matcher
- `PostToolUse` and `PermissionRequest` are not supported in v1

Existing `Notification` matchers in Claude settings do not have a direct Codex equivalent, so they are treated as `ask` during fallback mapping.

## Behavior Differences from Claude Code

`codex-hooks` does not fully emulate Claude Code's hook runtime.

- Claude `Stop` is mapped to Codex `TaskComplete` and `TurnAborted`
- Claude `Notification` is approximated as `TaskComplete` with the `ask` matcher
- The `ask` matcher is inferred heuristically from the final assistant message

The `ask` matcher is currently selected when the final assistant message:

- Ends with `?` or `？`
- Contains numbered options such as `1.` and `2.`

This makes the behavior similar in common cases, but not identical to Claude Code.

## Hook stdin Payload

Each hook command receives JSON on stdin:

```json
{
  "event_name": "TaskComplete",
  "matched_matcher": "ask",
  "session_path": "/Users/you/.codex/sessions/2026/03/07/session.jsonl",
  "cwd": "/Users/you/work/repo",
  "turn_id": "turn-12",
  "assistant_message": "Do you want me to continue?",
  "raw_event": {
    "type": "event_msg",
    "payload": {
      "type": "task_complete"
    }
  }
}
```

## Hook Protocol Limitations

`codex-hooks` currently supports command execution, but not Claude's full hook control protocol.

Each hook command receives normalized JSON on stdin, but Claude-specific hook fields are not provided. For example, fields such as `stop_hook_active` are not available unless `codex-hooks` explicitly implements them.

Hook stdout is also not interpreted as Claude control output. If a hook prints JSON such as:

```json
{"decision":"block","reason":"Run the finalizing workflow"}
```

`codex-hooks` will not use that response to continue, block, or redirect the Codex session.

This means hooks that rely on Claude's runtime behavior, rather than plain shell execution, will not behave the same way under `codex-hooks`.

## Example: Why Some Claude Stop Hooks Do Not Fully Work

A hook like `auto-commit-on-stop.sh` may work in Claude Code because it does not perform the final action by itself. Instead, it returns a control response such as:

```json
{"decision":"block","reason":"Run the finalizing workflow"}
```

Claude can interpret that response and continue the task accordingly.

`codex-hooks` does not currently implement that response protocol. It runs the hook command, but it does not interpret the returned JSON as an instruction to start another Codex task.

As a result, direct shell hooks can be reused, but Claude hooks that depend on Claude's own control loop cannot yet be reproduced exactly.

## How It Works

1. The `codex` wrapper launches the real Codex CLI.
2. A background monitor discovers the matching file under `~/.codex/sessions/**/*.jsonl`.
3. The monitor selects the session file that matches the current working directory and launch time.
4. JSONL events are normalized into `TaskStarted`, `TaskComplete`, or `TurnAborted`.
5. Matching hook groups are loaded from configuration and executed through `/bin/sh -lc`.

## Test

```sh
python3 -m unittest
```

The test suite includes a smoke test that runs `install.py` and `uninstall.py` against a clean temporary `HOME`, so CI verifies the install flow without relying on the maintainer's dotfiles.

## License

MIT
