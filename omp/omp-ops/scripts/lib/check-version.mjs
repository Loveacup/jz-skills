import { existsSync, mkdirSync } from "node:fs";
import {
  CACHE_TTL_SECONDS,
  GITHUB_BRANCH,
  GITHUB_REPO,
  GITHUB_SKILL_DIR,
  OFFICIAL_BRANCH,
  OFFICIAL_REPO,
  REFS_DIR,
  cacheDir,
  cacheFile,
  dirtyMarker,
  fetchJson,
  fetchText,
  gitDirty,
  gitRoot,
  isSemverish,
  jsonOut,
  readText,
  runText,
  versionBase,
  versionGt,
  versionRevision,
} from "./common.mjs";

function normalizeLocalOmp(raw) {
  return (raw || "unknown").replace(/^(omp\/|omp v|v)/, "").replace(/\s+/g, "") || "unknown";
}

async function main() {
  const localSkillRaw = readText(`${REFS_DIR}/VERSION`, "0.0.0-0").trim();
  const localSkill = isSemverish(localSkillRaw, true) ? localSkillRaw : "0.0.0-0";

  const localOmp = normalizeLocalOmp(runText("omp", ["--version"], { silent: true, fallback: "unknown" }));

  let githubSkill = "0.0.0-0";
  try {
    githubSkill = (await fetchText(`https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/${GITHUB_SKILL_DIR}/references/VERSION`)).trim();
  } catch {
    githubSkill = "0.0.0-0";
  }
  if (!isSemverish(githubSkill, true)) githubSkill = "0.0.0-0";

  let officialOmp = "unknown";
  try {
    const pkg = await fetchJson(`https://raw.githubusercontent.com/${OFFICIAL_REPO}/${OFFICIAL_BRANCH}/packages/coding-agent/package.json`);
    officialOmp = String(pkg.version || "unknown");
  } catch {
    officialOmp = "unknown";
  }
  if (!isSemverish(officialOmp)) officialOmp = "unknown";

  const localBase = versionBase(localSkill);
  const githubBase = versionBase(githubSkill);
  const localRev = versionRevision(localSkill);
  const githubRev = versionRevision(githubSkill);
  let status = "synced";
  let message = "All aligned.";
  const actions = [];
  const addAction = (action) => {
    if (!actions.includes(action)) actions.push(action);
  };

  if (officialOmp !== "unknown" && versionGt(officialOmp, githubBase)) {
    status = "sync-official";
    addAction("sync-from-official");
    addAction("push-to-github");
    message = `Official OMP (${officialOmp}) is newer than jz-skills skill (${githubSkill}). Recommended: sync-from-official, then push-to-github.`;
  } else if (versionGt(githubBase, localBase)) {
    status = "sync-github";
    addAction("sync-from-github");
    message = `jz-skills skill (${githubSkill}) is newer than local (${localSkill}). Recommended: sync-from-github.`;
  } else if (githubBase === localBase) {
    if (githubRev > localRev) {
      status = "sync-github";
      addAction("sync-from-github");
      message = `jz-skills skill revision (${githubSkill}) is newer than local (${localSkill}). Recommended: sync-from-github.`;
    } else if (localRev > githubRev) {
      status = "push-github";
      addAction("push-to-github");
      message = `Local skill revision (${localSkill}) is newer than jz-skills (${githubSkill}). Recommended: push-to-github.`;
    }
  } else if (versionGt(localBase, githubBase)) {
    status = "push-github";
    addAction("push-to-github");
    message = `Local skill (${localSkill}) is newer than jz-skills (${githubSkill}). Recommended: push-to-github.`;
  }

  const root = gitRoot();
  const localDirty = existsSync(dirtyMarker()) || gitDirty(root);
  if (localDirty && status === "synced") {
    status = "push-github";
    addAction("push-to-github");
    message = "Local skill has uncommitted changes. Recommended: push-to-github.";
  }

  // Cache handling (informational only; does not override status/actions)
  let recentSync = false;
  const cfile = cacheFile();
  if (existsSync(cfile)) {
    const last = Number(readText(cfile, "0").trim());
    const now = Math.floor(Date.now() / 1000);
    if (Number.isFinite(last) && now - last < CACHE_TTL_SECONDS) {
      recentSync = true;
    }
  }
  mkdirSync(cacheDir(), { recursive: true });

  jsonOut({
    local_omp: localOmp,
    local_skill: localSkill,
    github_skill: githubSkill,
    official_omp: officialOmp,
    status,
    actions,
    local_dirty: localDirty,
    recent_sync: recentSync,
    message,
  });
}

main().catch((err) => {
  jsonOut({ status: "error", message: err.message }, process.stderr);
  process.exit(1);
});
