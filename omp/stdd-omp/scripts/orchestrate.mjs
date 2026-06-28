#!/usr/bin/env node
/**
 * STDD-OMP orchestrator — cross-OS detection + optional GitHub version sync.
 *
 * Primary entry: CLI (`node scripts/orchestrate.mjs ...`).
 * ES module dynamic import works in some environments (e.g. Node) but not all
 * Bun/OMP eval contexts; use CLI for cross-OS reliability.
 *
 * Responsibilities:
 * 1. Detect whether the opt-in native-lane hook and custom auditor are installed.
 * 2. Compare local `references/VERSION` with the latest GitHub release
 *    (requires `STDD_OMP_GITHUB_REPO=Loveacup/jz-skills` or `--repo Loveacup/jz-skills`).
 * 3. Emit a JSON status object; perform installs only when explicitly requested.
 *
 * Exit codes (status mode):
 *   0  all green / no action needed
 *   1  runtime error
 *   2  missing opt-in hook/agent (installable)
 *   3  local version behind remote
 *
 * Usage:
 *   node scripts/orchestrate.mjs                         # status only, read-only
 *   node scripts/orchestrate.mjs --repo Loveacup/jz-skills       # include version check
 *   node scripts/orchestrate.mjs --install               # install missing only
 *   node scripts/orchestrate.mjs --install --force       # install + overwrite
 *   STDD_OMP_GITHUB_REPO=Loveacup/jz-skills node scripts/orchestrate.mjs --install
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import https from 'node:https';
import child_process from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const EXIT_OK = 0;
const EXIT_ERROR = 1;
const EXIT_MISSING = 2;
const EXIT_BEHIND = 3;

function skillRoot() {
  const thisFile = fileURLToPath(import.meta.url);
  return path.resolve(path.dirname(thisFile), '..');
}

function homeDir() {
  return os.homedir();
}

function nativeAgentDir() {
  if (process.env.PI_CODING_AGENT_DIR) {
    return process.env.PI_CODING_AGENT_DIR;
  }
  const configDir = process.env.PI_CONFIG_DIR || path.join(homeDir(), '.omp');
  return path.join(configDir, 'agent');
}

function hookTarget() {
  return path.join(nativeAgentDir(), 'hooks', 'pre', 'stdd-gate.ts');
}

function auditorTarget() {
  return path.join(nativeAgentDir(), 'agents', 'stdd-auditor.md');
}

function hookSource() {
  return path.join(skillRoot(), 'assets', 'stdd-gate.hook.ts');
}

function auditorSource() {
  return path.join(skillRoot(), 'assets', 'stdd-auditor.agent.md');
}

function versionFile() {
  return path.join(skillRoot(), 'references', 'VERSION');
}

function fileExists(filePath) {
  try {
    const st = fs.statSync(filePath);
    return st.isFile() && st.size > 0;
  } catch {
    return false;
  }
}

function directoryExists(dirPath) {
  try {
    return fs.statSync(dirPath).isDirectory();
  } catch {
    return false;
  }
}

function rootNonEmpty() {
  const dir = nativeAgentDir();
  if (!directoryExists(dir)) return false;
  return fs.readdirSync(dir).length > 0;
}

export function detect() {
  return {
    native_agent_root: nativeAgentDir(),
    root_nonempty: rootNonEmpty(),
    hook: {
      installed: fileExists(hookTarget()),
      source: hookSource(),
      target: hookTarget(),
    },
    auditor: {
      installed: fileExists(auditorTarget()),
      source: auditorSource(),
      target: auditorTarget(),
    },
  };
}

export function readLocalVersion() {
  try {
    return fs.readFileSync(versionFile(), 'utf8').trim();
  } catch {
    return null;
  }
}

function ompCompatibilityFile() {
  return path.join(skillRoot(), 'references', 'OMP_COMPATIBILITY');
}

export function readOmpCompatibility() {
  try {
    return fs.readFileSync(ompCompatibilityFile(), 'utf8').trim();
  } catch {
    return '>=16.1.0';
  }
}

export function readOmpVersion() {
  try {
    const result = child_process.spawnSync('omp', ['--version'], {
      encoding: 'utf8',
      timeout: 10000,
      shell: false,
    });
    if (result.error || result.status !== 0) return null;
    const match = result.stdout.match(/omp\/(\d+\.\d+\.\d+)/);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

function parseVersion(v) {
  return v.split('.').map((n) => parseInt(n, 10));
}

function cmpVersion(a, b) {
  const aa = parseVersion(a);
  const bb = parseVersion(b);
  for (let i = 0; i < Math.max(aa.length, bb.length); i++) {
    const x = aa[i] || 0;
    const y = bb[i] || 0;
    if (x > y) return 1;
    if (x < y) return -1;
  }
  return 0;
}

export function checkOmpCompatibility(ompVersion, requirement) {
  if (!ompVersion) return { compatible: null, reason: 'omp version not detected' };
  if (!requirement) return { compatible: true, reason: 'no requirement specified' };
  const m = requirement.match(/^(>=|<=|>|<|=)?\s*(.+)$/);
  const op = m ? m[1] || '>=' : '>=';
  const target = m ? m[2].trim() : requirement.trim();
  const c = cmpVersion(ompVersion, target);
  let ok;
  switch (op) {
    case '>=': ok = c >= 0; break;
    case '>': ok = c > 0; break;
    case '<=': ok = c <= 0; break;
    case '<': ok = c < 0; break;
    case '=':
    case '==': ok = c === 0; break;
    default: ok = c >= 0;
  }
  return {
    compatible: ok,
    reason: ok
      ? `OMP ${ompVersion} satisfies ${op}${target}`
      : `OMP ${ompVersion} does NOT satisfy ${op}${target}`,
  };
}

function normalizeVersion(tag) {
  return tag.replace(/^v/, '').trim();
}

function normalizeRepo(input) {
  if (!input) return null;
  const trimmed = input.trim();
  if (/^[\w.-]+\/[\w.-]+$/.test(trimmed)) return trimmed;
  try {
    const url = new URL(trimmed);
    const parts = url.pathname.replace(/^\/+|\/+$/g, '').split('/');
    if (parts.length >= 2) return `${parts[0]}/${parts[1]}`;
  } catch {
    // fall through
  }
  return null;
}

function httpsGetJson(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      {
        headers: {
          Accept: 'application/vnd.github+json',
          'User-Agent': `stdd-omp-orchestrator/${readLocalVersion() || '0.1.2'}`,
        },
      },
      (res) => {
        let body = '';
        res.on('data', (chunk) => {
          body += chunk;
        });
        res.on('end', () => {
          if (res.statusCode < 200 || res.statusCode >= 300) {
            reject(new Error(`GitHub API ${res.statusCode}`));
            return;
          }
          try {
            resolve(JSON.parse(body));
          } catch (e) {
            reject(new Error(`invalid JSON: ${e.message}`));
          }
        });
      }
    );
    req.on('error', reject);
    req.setTimeout(15000, () => {
      req.destroy();
      reject(new Error('request timeout'));
    });
  });
}

export async function checkRemote(repo) {
  const normalized = normalizeRepo(repo);
  if (!normalized) return { configured: false, repo: null, version: null, error: null };
  const url = `https://api.github.com/repos/${normalized}/releases/latest`;
  try {
    const data = await httpsGetJson(url);
    const version = normalizeVersion(data.tag_name || '');
    return { configured: true, repo: normalized, version, error: null };
  } catch (e) {
    return { configured: true, repo: normalized, version: null, error: e.message };
  }
}

function compareVersions(local, remote) {
  if (!local || !remote) return 'unknown';
  if (local === remote) return 'synced';
  const parts = [local, remote].map((v) => v.split('.').map(Number));
  for (let i = 0; i < Math.max(parts[0].length, parts[1].length); i++) {
    const a = parts[0][i] || 0;
    const b = parts[1][i] || 0;
    if (a > b) return 'ahead';
    if (a < b) return 'behind';
  }
  return 'synced';
}

export function planActions(status) {
  const actions = [];
  if (!status.root_nonempty) {
    actions.push({
      type: 'warning',
      message: `native agent root (${status.native_agent_root}) is empty or missing; OMP may not discover hooks/agents.`,
    });
  }
  // stdd-gate hook is optional opt-in; not auto-prompted.
  // The asset template remains available in assets/stdd-gate.hook.ts for manual opt-in.
  if (status.sync_status === 'behind') {
    actions.push({
      type: 'sync-version',
      message: `local ${status.local_version} is behind remote ${status.remote_version}; consider updating`,
    });
  }
  return actions;
}

export function installHook({ force = false } = {}) {
  const source = hookSource();
  const target = hookTarget();
  if (!fileExists(source)) {
    return { ok: false, skipped: false, target, error: `source missing: ${source}` };
  }
  if (fileExists(target) && !force) {
    return { ok: true, skipped: true, target, message: 'already installed; use --force to overwrite' };
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
  return { ok: true, skipped: false, target };
}

export function installAuditor({ force = false } = {}) {
  const source = auditorSource();
  const target = auditorTarget();
  if (!fileExists(source)) {
    return { ok: false, skipped: false, target, error: `source missing: ${source}` };
  }
  if (fileExists(target) && !force) {
    return { ok: true, skipped: true, target, message: 'already installed; use --force to overwrite' };
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
  return { ok: true, skipped: false, target };
}

export async function run({ githubRepo = process.env.STDD_OMP_GITHUB_REPO || process.env.STDD_OMP_REPO } = {}) {
  const detection = detect();
  const localVersion = readLocalVersion();
  const remote = await checkRemote(githubRepo);
  const syncStatus = remote.version
    ? compareVersions(localVersion, remote.version)
    : 'unknown';

  const ompVersion = readOmpVersion();
  const ompRequirement = readOmpCompatibility();
  const ompCompat = checkOmpCompatibility(ompVersion, ompRequirement);

  const status = {
    local_version: localVersion,
    remote_version: remote.version,
    remote_repo: remote.repo,
    sync_status: syncStatus,
    remote_error: remote.error,
    omp_version: ompVersion,
    omp_compatibility: ompRequirement,
    omp_compatible: ompCompat.compatible,
    omp_compatibility_reason: ompCompat.reason,
    ...detection,
  };
  const actions = planActions(status);
  if (githubRepo && !remote.configured) {
    actions.push({
      type: 'warning',
      message: `Invalid GitHub repo format: ${githubRepo}; expected a string like Loveacup/jz-skills or https://github.com/Loveacup/jz-skills`,
    });
  }
  if (ompCompat.compatible === false) {
    actions.push({
      type: 'warning',
      message: ompCompat.reason,
    });
  }
  status.actions = actions;
  return status;
}

function formatTextReport(status) {
  const lines = [];
  lines.push('STDD-OMP v' + status.local_version + ' | OMP ' + status.omp_version + ' | ' + (status.omp_compatible ? 'compatible' : 'incompatible'));
  lines.push('');
  if (status.actions.length === 0) {
    lines.push('✅ All components installed. No action needed.');
    return lines.join('\n');
  }
  // Only warnings and sync-status arrive here; opt-in components are no longer auto-prompted.
  const warnings = status.actions.filter(a => a.type === 'warning');
  for (const w of warnings) {
    lines.push('⚠️  ' + w.message);
  }
  if (status.sync_status === 'behind') {
    lines.push('');
    lines.push('Skill is behind remote (' + status.local_version + ' → ' + status.remote_version + '). Run git pull or re-install.');
  }
  return lines.join('\n');
}

function exitCodeFromStatus(status) {
  if (status.sync_status === 'behind') return EXIT_BEHIND;
  return EXIT_OK;
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const opts = {};
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--repo') opts.githubRepo = args[++i];
    else if (a === '--install') opts.install = true;
    else if (a === '--with-hook') opts.withHook = true;
    else if (a === '--force') opts.force = true;
    else if (a === '--dry-run') opts.dryRun = true;
    else if (a === '--text') opts.text = true;
  }
  return opts;
}

function isMainModule() {
  try {
    const main = process.argv[1];
    if (!main) return false;
    return import.meta.url === pathToFileURL(main).href;
  } catch {
    return false;
  }
}

async function main() {
  const opts = parseArgs(process.argv);
  if (opts.install || opts.dryRun) {
    const status = await run({ githubRepo: opts.githubRepo });
    console.log(JSON.stringify({ mode: opts.dryRun ? 'dry-run' : 'install', status }, null, 2));

    if (opts.dryRun) {
      process.exit(exitCodeFromStatus(status));
    }

    // Only install hook when explicitly opted in with --with-hook
    if (opts.withHook) {
      const results = {};
      results.hook = installHook({ force: opts.force });
      console.log(JSON.stringify({ installed: results }, null, 2));
      const failed = Object.values(results).some((r) => r && !r.ok);
      if (failed) process.exit(EXIT_ERROR);
    }

    const postStatus = await run({ githubRepo: opts.githubRepo });
    process.exit(exitCodeFromStatus(postStatus));
  }

  const status = await run({ githubRepo: opts.githubRepo });
  if (opts.text) { console.log(formatTextReport(status)); } else { console.log(JSON.stringify(status, null, 2)); }
  process.exit(exitCodeFromStatus(status));
}

if (isMainModule()) {
  main().catch((e) => {
    console.error(JSON.stringify({ error: e.message }, null, 2));
    process.exit(EXIT_ERROR);
  });
}
