import { existsSync, mkdirSync, rmdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { SCRIPT_DIR, SKILL_DIR, cacheDir, cacheFile, jsonOut, run } from "./common.mjs";

const actionMap = {
  "sync-from-official": "sync-from-official.mjs",
  "sync-from-github": "sync-from-github.mjs",
  "push-to-github": "push-to-github.mjs",
};

function main() {
  mkdirSync(cacheDir(), { recursive: true });
  const lockDir = path.join(SKILL_DIR, ".orchestrate.lock");
  try {
    mkdirSync(lockDir);
  } catch {
    jsonOut({ status: "locked", message: "Another sync is already running." });
    return;
  }
  try {
    const check = run(process.execPath, [path.join(SCRIPT_DIR, "lib", "check-version.mjs")]);
    if (check.status !== 0) {
      jsonOut({ status: "error", message: "check-version failed" }, process.stderr);
      process.exit(1);
    }
    let statusJson;
    try {
      statusJson = JSON.parse(check.stdout);
    } catch {
      jsonOut({ status: "error", message: "check-version returned invalid JSON" }, process.stderr);
      process.stderr.write(check.stdout);
      process.exit(1);
    }
    const actions = Array.isArray(statusJson.actions) ? statusJson.actions : [];
    if (actions.length === 0) {
      writeFileSync(cacheFile(), `${Math.floor(Date.now() / 1000)}\n`);
      jsonOut(statusJson);
      return;
    }
    for (const action of actions) {
      const script = actionMap[action];
      if (!script) {
        jsonOut({ status: "error", message: `Unknown action: ${action}` }, process.stderr);
        process.exit(1);
      }
      const result = run(process.execPath, [path.join(SCRIPT_DIR, "lib", script)], { stdio: "inherit" });
      if (result.status !== 0) {
        jsonOut({ status: "error", message: `Action failed: ${action}` }, process.stderr);
        process.exit(1);
      }
    }
    writeFileSync(cacheFile(), `${Math.floor(Date.now() / 1000)}\n`);
    jsonOut(statusJson);
  } finally {
    if (existsSync(lockDir)) rmdirSync(lockDir);
  }
}

main();
