export interface HookCommand {
  type: "command";
  command: string;
}

export interface HookGroup {
  matcher: string;
  hooks: HookCommand[];
}

export type HooksConfig = Record<string, HookGroup[]>;

export interface ClaudeSettings {
  hooks?: HooksConfig;
}

export interface HookResult {
  command: string;
  exitCode: number | null;
  stdout: string;
  stderr: string;
}

export interface FireResult {
  event: string;
  matcher: string;
  results: HookResult[];
}
