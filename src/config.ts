import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import assert from "node:assert";
import type { HooksConfig, ClaudeSettings } from "./types.js";

const DEFAULT_SETTINGS_PATH: string = join(
  homedir(),
  ".claude",
  "settings.json"
);

export async function loadHooksConfig(
  settingsPath: string = DEFAULT_SETTINGS_PATH
): Promise<HooksConfig> {
  const raw: string = await readFile(settingsPath, "utf-8");
  const settings: ClaudeSettings = JSON.parse(raw) as ClaudeSettings;
  assert(settings.hooks != null, `No hooks section found in ${settingsPath}`);
  return settings.hooks;
}
