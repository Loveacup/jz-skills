import { mkdirSync } from "node:fs";
import path from "node:path";
import {
  OFFICIAL_BRANCH,
  OFFICIAL_DIR,
  OFFICIAL_REPO,
  REFS_DIR,
  dirtyMarker,
  fetchJson,
  fetchText,
  jsonOut,
  readText,
  touch,
  writeText,
} from "./common.mjs";

const DOCS = [
  "environment-variables.md",
  "providers.md",
  "skills.md",
  "custom-tools.md",
  "mcp-config.md",
  "models.md",
];

async function main() {
  mkdirSync(OFFICIAL_DIR, { recursive: true });
  const versionUrl = `https://raw.githubusercontent.com/${OFFICIAL_REPO}/${OFFICIAL_BRANCH}/packages/coding-agent/package.json`;
  let officialVersion = "unknown";
  try {
    const pkg = await fetchJson(versionUrl);
    officialVersion = String(pkg.version || "unknown");
  } catch {
    officialVersion = "unknown";
  }
  if (!officialVersion || officialVersion === "unknown") {
    jsonOut({ status: "error", message: `Failed to fetch official OMP version from ${versionUrl}` }, process.stderr);
    process.exit(1);
  }

  for (const doc of DOCS) {
    const url = `https://raw.githubusercontent.com/${OFFICIAL_REPO}/${OFFICIAL_BRANCH}/docs/${doc}`;
    try {
      writeText(path.join(OFFICIAL_DIR, doc), await fetchText(url));
    } catch {
      jsonOut({ status: "error", message: `Failed to download doc: ${doc}` }, process.stderr);
      process.exit(1);
    }
  }

  const changelogUrl = `https://raw.githubusercontent.com/${OFFICIAL_REPO}/${OFFICIAL_BRANCH}/packages/coding-agent/CHANGELOG.md`;
  try {
    const changelog = await fetchText(changelogUrl);
    writeText(path.join(OFFICIAL_DIR, "CHANGELOG.md"), `${changelog.split(/\r?\n/).slice(0, 500).join("\n")}\n`);
  } catch {
    jsonOut({ status: "error", message: `Failed to download CHANGELOG from ${changelogUrl}` }, process.stderr);
    process.exit(1);
  }

  const versionPath = path.join(REFS_DIR, "VERSION");
  const currentVersion = readText(versionPath, "").trim();
  const currentBase = currentVersion.match(/^(\d+\.\d+\.\d+)(?:-(\d+))?$/);
  const revision = currentBase?.[1] === officialVersion ? (currentBase[2] || "0") : "0";
  writeText(versionPath, `${officialVersion}-${revision}\n`);
  const syncStatePath = path.join(REFS_DIR, "sync-state.json");
  let state = {};
  try {
    state = JSON.parse(readText(syncStatePath, "{}"));
  } catch {
    state = {};
  }
  state = {
    ...state,
    official_omp: officialVersion,
    synced_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00"),
    source: `${OFFICIAL_REPO} ${OFFICIAL_BRANCH}`,
  };
  writeText(syncStatePath, `${JSON.stringify(state, null, 2)}\n`);
  touch(dirtyMarker());
  jsonOut({ status: "ok", official_omp: officialVersion, message: "Synced from official OMP." });
}

main().catch((err) => {
  jsonOut({ status: "error", message: err.message }, process.stderr);
  process.exit(1);
});
