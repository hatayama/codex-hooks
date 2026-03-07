# codex-hooks

Codex CLI の session JSONL を監視し、Claude Code 風の hooks を Codex でも再現する macOS 向けの Python ツール。

`codex-notify` のような通知やタブタイトル変更はこのリポジトリの責務に含めず、純粋に「いつ hook を発火するか」と「何の command を実行するか」だけを扱う。

## Install

```sh
git clone https://github.com/hatayama/codex-hooks.git
cd codex-hooks
python3 install.py
source ~/.zshrc
```

インストール後は `codex` シェル関数が追加され、実際の Codex CLI を起動しつつバックグラウンドで session monitor を立ち上げる。

無効化したいときは:

```sh
CODEX_HOOKS_DISABLE=1 codex ...
```

## Configuration Priority

1. `~/.codex/hooks.json`
2. `~/.claude/settings.json`

`~/.codex/hooks.json` があればそれを優先し、無ければ Claude の `settings.json` をフォールバックとして使う。

## Codex Hooks Format

`~/.codex/hooks.json` は Claude と同じ `hooks` 構造を使う。

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
- `ask` は assistant の最終メッセージが質問文または番号付き選択肢で終わるとき

### `TurnAborted`

- Source: `event_msg.payload.type == "turn_aborted"`
- Supported matcher: `""`, `aborted`

## Claude Fallback Mapping

`~/.claude/settings.json` を使う場合は、次のルールで Codex イベントへ寄せる。

- `Stop` hooks:
  - `TaskComplete`
  - `TurnAborted`
- `Notification` hooks:
  - `TaskComplete` の `ask` 完了時
- `UserPromptSubmit`
- `PreToolUse`
- `PostToolUse`
- `PermissionRequest`
  - v1 では未対応

`Notification` の既存 matcher は Codex に対応する値が無いため、フォールバック時は `ask` 扱いで実行する。

## Hook stdin Payload

各 hook command の stdin には JSON が渡る。

```json
{
  "event_name": "TaskComplete",
  "matched_matcher": "ask",
  "session_path": "/Users/you/.codex/sessions/2026/03/07/session.jsonl",
  "cwd": "/Users/you/work/repo",
  "turn_id": "turn-12",
  "assistant_message": "この方針で進めますか？",
  "raw_event": {
    "type": "event_msg",
    "payload": {
      "type": "task_complete"
    }
  }
}
```

## How It Works

1. `codex` ラッパーが本物の Codex CLI を起動する
2. 同時に monitor が `~/.codex/sessions/**/*.jsonl` を探索する
3. `cwd` と起動時刻に一致する session file を選ぶ
4. JSONL イベントを `TaskStarted` / `TaskComplete` / `TurnAborted` に正規化する
5. 設定ファイルから対応する hook group を探し、`/bin/sh -lc` で command を実行する

## Test

```sh
python3 -m unittest
```

## License

MIT
