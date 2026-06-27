import { existsSync, mkdirSync, rmdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { SCRIPT_DIR, SKILL_DIR, cacheDir, cacheFile, jsonOut, run } from "./common.mjs";

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
    if (actions.length > 0) {
      statusJson.message = `${statusJson.message || ""} These actions are recommended but will not be run automatically. Run them manually: ${actions.map((a) => path.join(SCRIPT_DIR, `${a}.sh`)).join(", ")}`;
    }
    jsonOut(statusJson);
  } finally {
    if (existsSync(lockDir)) rmdirSync(lockDir);
  }
}

main();
