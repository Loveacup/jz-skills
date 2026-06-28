import { GITHUB_BRANCH, GITHUB_REPO, GITHUB_SKILL_DIR, gitRoot, gitDirty, jsonOut, run } from "./common.mjs";

function main() {
  const root = gitRoot();
  if (!root) {
    jsonOut({ status: "error", message: "Skill directory is not inside a git repository." }, process.stderr);
    process.exit(1);
  }
  let result = run("git", ["-C", root, "fetch", "origin", GITHUB_BRANCH]);
  if (result.status !== 0) {
    jsonOut({ status: "error", message: `Failed to fetch origin/${GITHUB_BRANCH} from ${GITHUB_REPO}` }, process.stderr);
    process.exit(1);
  }
  result = run("git", ["-C", root, "ls-tree", `origin/${GITHUB_BRANCH}`, GITHUB_SKILL_DIR]);
  if (result.status !== 0 || !result.stdout.trim()) {
    jsonOut({ status: "no_remote", message: `Remote skill directory not yet present on origin/main: ${GITHUB_SKILL_DIR}` });
    return;
  }
  if (gitDirty(root)) {
    jsonOut({ status: "error", message: `Local skill directory has uncommitted changes; refusing to overwrite: ${GITHUB_SKILL_DIR}` }, process.stderr);
    process.exit(1);
  }
  result = run("git", ["-C", root, "checkout", `origin/${GITHUB_BRANCH}`, "--", GITHUB_SKILL_DIR]);
  if (result.status !== 0) {
    jsonOut({ status: "error", message: `Failed to checkout ${GITHUB_SKILL_DIR} from origin/main.` }, process.stderr);
    process.exit(1);
  }
  jsonOut({ status: "ok", message: `Pulled ${GITHUB_SKILL_DIR} from origin/${GITHUB_BRANCH}.` });
}

main();
