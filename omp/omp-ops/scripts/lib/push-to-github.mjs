import path from "node:path";
import { GITHUB_BRANCH, GITHUB_SKILL_DIR, REFS_DIR, dirtyMarker, gitRoot, jsonOut, readText, remove, run, touch } from "./common.mjs";

function restoreDirtyOnError(version) {
  touch(dirtyMarker());
  jsonOut({ status: "error", message: `Failed to push omp-ops ${version}. Dirty marker restored.` }, process.stderr);
  process.exit(1);
}

function main() {
  const version = readText(path.join(REFS_DIR, "VERSION"), "0.0.0-0").trim() || "0.0.0-0";
  const root = gitRoot();
  if (!root) {
    jsonOut({ status: "error", message: "Skill directory is not inside a git repository." }, process.stderr);
    process.exit(1);
  }

  remove(dirtyMarker());
  let result = run("git", ["-C", root, "status", "--porcelain", "--", GITHUB_SKILL_DIR]);
  if (result.status !== 0 || !result.stdout.trim()) {
    jsonOut({ status: "no_changes", message: `No changes to commit for omp-ops ${version}.` });
    return;
  }

  result = run("git", ["-C", root, "add", GITHUB_SKILL_DIR], { stdio: "inherit" });
  if (result.status !== 0) restoreDirtyOnError(version);

  result = run("git", ["-C", root, "diff", "--cached", "--quiet"]);
  if (result.status === 0) {
    jsonOut({ status: "no_changes", message: `Nothing staged for omp-ops ${version}.` });
    return;
  }

  result = run("git", ["-C", root, "commit", "-m", `sync: omp-ops ${version}`], { stdio: "inherit" });
  if (result.status !== 0) restoreDirtyOnError(version);

  result = run("git", ["-C", root, "push", "origin", GITHUB_BRANCH], { stdio: "inherit" });
  if (result.status !== 0) restoreDirtyOnError(version);

  jsonOut({ status: "ok", message: `Pushed omp-ops ${version} to origin/main.`, version });
}

main();
