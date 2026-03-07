import { execFile } from "node:child_process";
import { homedir } from "node:os";
import type {
  HooksConfig,
  HookGroup,
  HookResult,
  FireResult,
} from "./types.js";

function expandTilde(command: string): string {
  if (command.startsWith("~/")) {
    return homedir() + command.slice(1);
  }
  return command;
}

function runCommand(command: string, stdin?: string): Promise<HookResult> {
  const expanded: string = expandTilde(command);
  const parts: string[] = expanded.split(/\s+/);
  const bin: string = parts[0];
  const args: string[] = parts.slice(1);

  return new Promise((resolve) => {
    const child = execFile(bin, args, (error, stdout, stderr) => {
      resolve({
        command,
        exitCode: error ? (typeof error.code === "number" ? error.code : 1) : 0,
        stdout: stdout.toString(),
        stderr: stderr.toString(),
      });
    });
    if (stdin != null && child.stdin != null) {
      child.stdin.write(stdin);
      child.stdin.end();
    }
  });
}

function matchesEvent(group: HookGroup, matcher: string): boolean {
  if (group.matcher === "") return true;
  return group.matcher === matcher;
}

export async function fireEvent(
  config: HooksConfig,
  event: string,
  matcher: string = "",
  stdin?: string
): Promise<FireResult[]> {
  const groups: HookGroup[] | undefined = config[event];
  if (groups == null) return [];

  const results: FireResult[] = [];

  for (const group of groups) {
    if (!matchesEvent(group, matcher)) continue;

    const hookResults: HookResult[] = await Promise.all(
      group.hooks.map((hook) => runCommand(hook.command, stdin))
    );

    results.push({ event, matcher: group.matcher, results: hookResults });
  }

  return results;
}
