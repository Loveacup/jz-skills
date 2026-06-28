import { cpSync, mkdirSync, symlinkSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { SKILL_DIR, jsonOut, remove } from "./common.mjs";

function main() {
  const targetDir = process.env.OMP_OPS_INSTALL_TARGET
    || path.join(os.homedir(), ".agents", "pools", "hermes-ops", "omp-ops");
  mkdirSync(path.dirname(targetDir), { recursive: true });
  remove(targetDir);
  let method = "symlink";
  try {
    symlinkSync(SKILL_DIR, targetDir, process.platform === "win32" ? "junction" : "dir");
  } catch {
    method = "copy";
    try {
      cpSync(SKILL_DIR, targetDir, { recursive: true });
    } catch {
      jsonOut({ status: "error", message: `Failed to install skill to ${targetDir}` }, process.stderr);
      process.exit(1);
    }
  }
  jsonOut({ status: "ok", source: SKILL_DIR, target: targetDir, method });
}

main();
