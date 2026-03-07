# codex-hooks

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) の hooks 設定 (`~/.claude/settings.json`) をそのまま再利用して、[Codex CLI](https://github.com/openai/codex) でも同じフックを実行できるようにする CLI / ライブラリ。

## Background

Claude Code にはエージェントのライフサイクルイベントに応じて任意のコマンドを実行できる **hooks** 機能がある。一方 Codex CLI には同等の機能がない。

このツールは Claude Code の hooks 設定をそのまま読み取り、任意のタイミングで発火させることで、Codex でも同じ通知やタブタイトル変更などの体験を実現する。

## Install

```sh
npm install -g codex-hooks
```

Or clone and link:

```sh
git clone https://github.com/hatayama/codex-hooks.git
cd codex-hooks
npm install && npm run build
npm link
```

## Usage

### CLI

```sh
# Stop イベントを発火（matcher が空のグループすべてが実行される）
codex-hooks fire Stop

# matcher を指定して Notification イベントを発火
codex-hooks fire Notification --matcher permission_prompt

# stdin データをフックコマンドに渡す
codex-hooks fire UserPromptSubmit --stdin '{"prompt":"hello"}'

# 別の settings.json を指定
codex-hooks fire Stop --config /path/to/settings.json
```

### Library

```ts
import { loadHooksConfig, fireEvent } from "codex-hooks";

const config = await loadHooksConfig();
await fireEvent(config, "Stop");
await fireEvent(config, "Notification", "permission_prompt");
```

## How It Works

### 1. 設定の読み込み

`~/.claude/settings.json` の `hooks` セクションを読む。フォーマットは Claude Code と完全に同一:

```jsonc
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",           // 空文字 = 常にマッチ
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/notify.py -t 'done'"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "permission_prompt",  // この値と一致した時だけ実行
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/notify.py -t 'need approval'"
          }
        ]
      }
    ]
  }
}
```

### 2. イベントのマッチング

`codex-hooks fire <event> [--matcher <value>]` が呼ばれると:

1. 設定から `event` に対応するフックグループ一覧を取得
2. 各グループの `matcher` をチェック:
   - `matcher` が空文字 → 常にマッチ（すべての呼び出しで実行）
   - `matcher` が非空 → `--matcher` で渡された値と完全一致する場合のみ実行
3. マッチしたグループ内の `hooks` をすべて並列実行

### 3. コマンドの実行

- `command` 文字列をスペースで分割し、`execFile` で実行
- `~/` で始まるパスはホームディレクトリに展開
- `--stdin` が指定されていれば、子プロセスの stdin にデータを書き込む
- 失敗したコマンドは stderr にエラーを出力するが、他のフックの実行は止めない

### Architecture

```
~/.claude/settings.json
        │
        │  loadHooksConfig()
        ▼
   ┌──────────┐
   │  config   │  JSON parse → hooks セクション抽出
   └────┬─────┘
        │
        │  fireEvent(config, event, matcher?, stdin?)
        ▼
   ┌──────────┐
   │  runner   │  matcher 照合 → execFile で並列実行
   └────┬─────┘
        │
        ▼
   hook commands (notify.py, tab_title.py, etc.)
```

## Supported Events

Claude Code のイベント名をそのまま使える:

| Event | Description |
|---|---|
| `UserPromptSubmit` | ユーザーがプロンプトを送信した |
| `PreToolUse` | ツール実行前 |
| `PostToolUse` | ツール実行後 |
| `Notification` | 通知イベント |
| `Stop` | エージェントが停止した |
| `PermissionRequest` | 権限リクエスト |

イベント名は自由に追加可能。設定 JSON に書かれていればどんなイベント名でも動作する。

## Integration with Codex

Codex CLI のラッパーシェル関数から呼び出す例:

```sh
codex_with_hooks() {
  codex-hooks fire UserPromptSubmit
  codex "$@"
  codex-hooks fire Stop
}
```

より高度な統合（セッション監視による自動検出）は [codex-notify](https://github.com/hatayama/codex-notify) を参照。

## License

MIT
