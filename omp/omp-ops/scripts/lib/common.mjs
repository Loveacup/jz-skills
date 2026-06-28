import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const OFFICIAL_REPO = "can1357/oh-my-pi";
export const OFFICIAL_BRANCH = "main";
export const GITHUB_REPO = "Loveacup/jz-skills";
export const GITHUB_BRANCH = "main";
export const GITHUB_SKILL_DIR = "omp/omp-ops";
export const CACHE_TTL_SECONDS = 300;

const THIS_FILE = fileURLToPath(import.meta.url);
export const LIB_DIR = path.dirname(THIS_FILE);
export const SCRIPT_DIR = path.dirname(LIB_DIR);
export const SKILL_DIR = path.dirname(SCRIPT_DIR);
export const REFS_DIR = path.join(SKILL_DIR, "references");
export const OFFICIAL_DIR = path.join(REFS_DIR, "official");

export function jsonOut(data, stream = process.stdout) {
  stream.write(`${JSON.stringify(data, null, 2)}\n`);
}

export function readText(file, fallback = "") {
  try {
    return readFileSync(file, "utf8");
  } catch {
    return fallback;
  }
}

export function writeText(file, value) {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, value, "utf8");
}

export function cacheDir() {
  if (process.env.XDG_CACHE_HOME) return process.env.XDG_CACHE_HOME;
  if (process.platform === "win32" && process.env.LOCALAPPDATA) {
    return path.join(process.env.LOCALAPPDATA, "omp-ops");
  }
  return path.join(os.homedir(), ".cache");
}

export function cacheFile() {
  return path.join(cacheDir(), "omp-ops-last-sync");
}

export function dirtyMarker() {
  return path.join(SKILL_DIR, ".dirty");
}

export function versionBase(v) {
  return /-\d+$/.test(v) ? v.replace(/-\d+$/, "") : v;
}

export function versionRevision(v) {
  const match = v.match(/-(\d+)$/);
  return match ? Number(match[1]) : 0;
}

export function isSemverish(v, allowRevision = false) {
  return new RegExp(`^\\d+\\.\\d+\\.\\d+${allowRevision ? "(-\\d+)?" : ""}$`).test(v);
}

export function versionGt(a, b) {
  if (!a || !b || a === "unknown" || b === "unknown") return false;
  const ap = versionBase(a).split(".").map((x) => Number(x || 0));
  const bp = versionBase(b).split(".").map((x) => Number(x || 0));
  for (let i = 0; i < 3; i += 1) {
    if ((ap[i] || 0) > (bp[i] || 0)) return true;
    if ((ap[i] || 0) < (bp[i] || 0)) return false;
  }
  return false;
}

export function run(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: options.cwd,
    encoding: "utf8",
    stdio: options.stdio || ["ignore", "pipe", "pipe"],
  });
}

export function runText(command, args, options = {}) {
  try {
    return execFileSync(command, args, {
      cwd: options.cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", options.silent ? "ignore" : "pipe"],
    });
  } catch {
    return options.fallback ?? "";
  }
}

export function gitRoot() {
  const out = runText("git", ["-C", SKILL_DIR, "rev-parse", "--show-toplevel"], {
    silent: true,
    fallback: "",
  }).trim();
  return out || "";
}

export function gitDirty(root) {
  if (!root) return false;
  const out = runText("git", ["-C", root, "status", "--porcelain", "--", GITHUB_SKILL_DIR], {
    silent: true,
    fallback: "",
  });
  return out.trim().length > 0;
}

export async function fetchText(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.text();
}

export async function fetchJson(url) {
  return JSON.parse(await fetchText(url));
}

export function touch(file) {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, existsSync(file) ? readFileSync(file) : "");
}

export function remove(file) {
  rmSync(file, { force: true, recursive: true });
}
