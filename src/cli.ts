#!/usr/bin/env node

import assert from "node:assert";
import { loadHooksConfig } from "./config.js";
import { fireEvent } from "./runner.js";
import type { HooksConfig, FireResult } from "./types.js";

function usage(): void {
  console.log(`Usage: codex-hooks fire <event> [--matcher <matcher>] [--config <path>] [--stdin <data>]

Events (Claude Code compatible):
  UserPromptSubmit   User submitted a prompt
  PreToolUse         Before a tool is used
  PostToolUse        After a tool is used
  Notification       Notification event
  Stop               Agent stopped
  PermissionRequest  Permission requested

Options:
  --matcher <matcher>   Match specific hook groups (default: all)
  --config <path>       Path to settings.json (default: ~/.claude/settings.json)
  --stdin <data>        Data to pass to hook commands via stdin`);
}

function parseArgs(args: string[]): {
  command: string;
  event: string;
  matcher: string;
  configPath: string | undefined;
  stdin: string | undefined;
} {
  assert(args.length >= 2, "Missing command and event");

  const command: string = args[0];
  const event: string = args[1];
  let matcher: string = "";
  let configPath: string | undefined;
  let stdin: string | undefined;

  for (let i: number = 2; i < args.length; i++) {
    if (args[i] === "--matcher" && i + 1 < args.length) {
      matcher = args[++i];
    } else if (args[i] === "--config" && i + 1 < args.length) {
      configPath = args[++i];
    } else if (args[i] === "--stdin" && i + 1 < args.length) {
      stdin = args[++i];
    }
  }

  return { command, event, matcher, configPath, stdin };
}

async function main(): Promise<void> {
  const args: string[] = process.argv.slice(2);

  if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
    usage();
    process.exit(0);
  }

  const parsed = parseArgs(args);
  assert(parsed.command === "fire", `Unknown command: ${parsed.command}`);

  const config: HooksConfig = await loadHooksConfig(parsed.configPath);
  const results: FireResult[] = await fireEvent(
    config,
    parsed.event,
    parsed.matcher,
    parsed.stdin
  );

  for (const result of results) {
    for (const hookResult of result.results) {
      if (hookResult.exitCode !== 0) {
        console.error(
          `[FAIL] ${hookResult.command} (exit: ${hookResult.exitCode})`
        );
        if (hookResult.stderr) console.error(hookResult.stderr);
      }
    }
  }
}

main();
