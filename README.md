# codex-hooks

`codex-hooks` is a macOS-focused Python tool that recreates Claude Code-style hooks for Codex by watching Codex session JSONL files.

This repository intentionally stays focused on hook reproduction. It does not own UI features such as desktop notifications or terminal title updates. Its job is only to decide when hooks should fire and which commands should run.

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

## Codex Hooks Format

`~/.codex/hooks.json` uses the same `hooks` structure as Claude:

```json
{
  "hooks": {
    "TaskStarted": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/tab_title.py -t '⚡ Codex'"
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
            "command": "~/.claude/hooks/notify.py -t 'done'"
          }
        ]
      },
      {
        "matcher": "ask",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/notify.py -t 'question'"
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
            "command": "~/.claude/hooks/notify.py -t 'aborted'"
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

- `Stop` hooks run on:
  - `TaskComplete`
  - `TurnAborted`
- `Notification` hooks run on:
  - `TaskComplete` with the `ask` matcher
- `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `PermissionRequest` are not supported in v1

Existing `Notification` matchers in Claude settings do not have a direct Codex equivalent, so they are treated as `ask` during fallback mapping.

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

## License

MIT
