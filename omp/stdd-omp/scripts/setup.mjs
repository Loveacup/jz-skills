#!/usr/bin/env node
/**
 * STDD-OMP first-time setup + environment doctor.
 *
 * Inspired by Agent-Reach's `doctor` + config flow:
 *   - Check environment (OMP version, skill lane, opt-in components).
 *   - Generate `~/.stdd/config.json` with user preferences.
 *   - `--apply` installs missing opt-in components (hook/auditor/rules/WATCHDOG).
 *   - Prints a human-readable report + recommended OMP `config.yml` snippet.
 *
 * This script never edits `~/.omp/agent/config.yml` directly; it only prints a
 * snippet and delegates OMP-specific config questions to `/skill:omp-ops`.
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const orchestratePath = fileURLToPath(new URL('./orchestrate.mjs', import.meta.url));
const o = await import(pathToFileURL(orchestratePath).href);

const gatesPath = fileURLToPath(new URL('./gates.mjs', import.meta.url));
const g = await import(pathToFileURL(gatesPath).href);

const STDD_DIR_NAME = '.stdd';
const CONFIG_FILE_NAME = 'config.json';

function homeDir() {
  return os.homedir();
}

function stdDir() {
  return path.join(homeDir(), STDD_DIR_NAME);
}

function userConfigFile() {
  return path.join(stdDir(), CONFIG_FILE_NAME);
}

function skillRoot() {
  const thisFile = fileURLToPath(import.meta.url);
  return path.resolve(path.dirname(thisFile), '..');
}

function nativeAgentDir() {
  if (process.env.PI_CODING_AGENT_DIR) {
    return process.env.PI_CODING_AGENT_DIR;
  }
  const configDir = process.env.PI_CONFIG_DIR || path.join(homeDir(), '.omp');
  return path.join(configDir, 'agent');
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

function listRuleFiles() {
  const dir = path.join(skillRoot(), 'assets', 'stdd-rules');
  if (!directoryExists(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.md'))
    .map((f) => ({ source: path.join(dir, f), name: f }));
}

function ruleSourceDir() {
  return path.join(skillRoot(), 'assets', 'stdd-rules');
}

function ruleTargetDir() {
  return path.join(nativeAgentDir(), 'rules');
}

function watchdogSource() {
  return path.join(skillRoot(), 'assets', 'WATCHDOG.md');
}

function watchdogYmlSource() {
  return path.join(skillRoot(), 'assets', 'WATCHDOG.yml');
}

function watchdogTarget() {
  return path.join(nativeAgentDir(), 'WATCHDOG.md');
}

function watchdogYmlTarget() {
  return path.join(nativeAgentDir(), 'WATCHDOG.yml');
}

function detectSkillLane() {
  const agentsPath = path.join(homeDir(), '.agents', 'skills', 'stdd-omp', 'SKILL.md');
  const nativePath = path.join(nativeAgentDir(), 'skills', 'stdd-omp', 'SKILL.md');
  if (fileExists(agentsPath)) return { lane: 'agents', path: path.dirname(agentsPath) };
  if (fileExists(nativePath)) return { lane: 'native', path: path.dirname(nativePath) };
  return { lane: 'unknown', path: skillRoot() };
}

function detectRules() {
  const target = ruleTargetDir();
  const files = listRuleFiles();
  const installed = files.length > 0 && files.every((f) => fileExists(path.join(target, f.name)));
  return {
    installed,
    source: ruleSourceDir(),
    target,
    files,
  };
}

function detectWatchdog() {
  return {
    installed: fileExists(watchdogTarget()),
    ymlInstalled: fileExists(watchdogYmlTarget()),
    source: watchdogSource(),
    ymlSource: watchdogYmlSource(),
    target: watchdogTarget(),
    ymlTarget: watchdogYmlTarget(),
  };
}

function readConfigYaml() {
  const configPath = path.join(nativeAgentDir(), 'config.yml');
  try {
    return fs.readFileSync(configPath, 'utf8');
  } catch {
    return '';
  }
}

function yamlHas(text, pattern) {
  return pattern.test(text);
}

function detectOmpConfig() {
  const text = readConfigYaml();
  const checks = {
    memory_backend_local: /memory:\s*\n(?:\s+\S+:\s*\S+\n)*?\s+backend:\s*local\b/m.test(text),
    modelRoles_plan: /modelRoles:\s*\n(?:\s+\S+:\s*\S+\n)*?\s+plan:/m.test(text),
    modelRoles_task: /modelRoles:\s*\n(?:\s+\S+:\s*\S+\n)*?\s+task:/m.test(text),
    modelRoles_advisor: /modelRoles:\s*\n(?:\s+\S+:\s*\S+\n)*?\s+advisor:/m.test(text),
    approvalMode: /tools:\s*\n(?:\s+\S+:\s*\S+\n)*?\s+approvalMode:/m.test(text),
    task_isolation: /task:\s*\n(?:\s+\S+:\s*\S+\n)*?\s+isolation:/m.test(text),
    task_async: /^(task):\s*\n.*\n\s+async:/m.test(text) || /^\s{0,2}task:\s*\n(?:\s+\S+:.*\n)*?\s+async:/m.test(text),
  };
  return {
    config_path: path.join(nativeAgentDir(), 'config.yml'),
    present: fileExists(path.join(nativeAgentDir(), 'config.yml')),
    checks,
  };
}

async function detectGatesSelfTest() {
  const results = {
    artifact_ok: false,
    test_pass_ok: false,
    test_fail_ok: false,
    danger_detected: false,
    clean_pass: false,
    counter_ok: false,
  };
  const reasons = [];

  try {
    const artifact = g.verifyArtifact(path.join(skillRoot(), 'scripts', 'gates.mjs'));
    results.artifact_ok = artifact.ok;
    if (!artifact.ok) reasons.push(`verifyArtifact: ${artifact.message}`);
  } catch (e) {
    reasons.push(`verifyArtifact exception: ${e.message}`);
  }

  try {
    const pass = await g.verifyTest('node -e "process.exit(0)"', { shell: false });
    results.test_pass_ok = pass.ok && pass.code === 0;
    if (!results.test_pass_ok) reasons.push(`verifyTest pass: code ${pass.code}`);
  } catch (e) {
    reasons.push(`verifyTest pass exception: ${e.message}`);
  }

  try {
    const fail = await g.verifyTest('node -e "process.exit(1)"', { shell: false });
    results.test_fail_ok = !fail.ok && fail.code === 1;
    if (!results.test_fail_ok) reasons.push(`verifyTest fail: code ${fail.code}`);
  } catch (e) {
    reasons.push(`verifyTest fail exception: ${e.message}`);
  }

  try {
    const danger = g.scanDanger('git push origin main');
    results.danger_detected = danger.matches.length > 0;
    if (!results.danger_detected) reasons.push('scanDanger did not detect git push');
  } catch (e) {
    reasons.push(`scanDanger exception: ${e.message}`);
  }

  try {
    const clean = g.scanDanger('ls -la');
    results.clean_pass = clean.matches.length === 0;
    if (!results.clean_pass) reasons.push(`scanDanger false positive: ${clean.matches.join(', ')}`);
  } catch (e) {
    reasons.push(`scanDanger clean exception: ${e.message}`);
  }

  try {
    const prevStateDir = process.env.STDD_STATE_DIR;
    const tmpState = path.join(os.tmpdir(), `stdd-selftest-${Date.now()}`);
    process.env.STDD_STATE_DIR = tmpState;
    const testKey = 'setup-selftest';
    const c1 = g.bumpCounter({ key: testKey, kind: 'regen', max: 3, action: 'incr' });
    const c2 = g.bumpCounter({ key: testKey, kind: 'regen', max: 3, action: 'reset' });
    const c3 = g.bumpCounter({ key: testKey, kind: 'regen', max: 3, action: 'get' });
    results.counter_ok = c1.ok && c1.count === 1 && c2.ok && c2.count === 0 && c3.ok && c3.count === 0;
    if (!results.counter_ok) reasons.push(`counter state mismatch: ${JSON.stringify({ c1, c2, c3 })}`);
    process.env.STDD_STATE_DIR = prevStateDir;
    fs.rmSync(tmpState, { recursive: true, force: true });
  } catch (e) {
    reasons.push(`counter exception: ${e.message}`);
  }

  const allOk = Object.values(results).every(Boolean);
  return {
    ok: allOk,
    results,
    reasons,
  };
}

function loadUserConfig() {
  const file = userConfigFile();
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return {};
  }
}

function saveUserConfig(config) {
  const dir = stdDir();
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(userConfigFile(), JSON.stringify(config, null, 2) + '\n', 'utf8');
}

function buildConfig(cliOpts, report) {
  const existing = loadUserConfig();
  return {
    github_repo: cliOpts.githubRepo || existing.github_repo || null,
    approval_mode: cliOpts.approvalMode || existing.approval_mode || 'write',
    components: {
      hook: cliOpts.withHook ?? existing.components?.hook ?? report.hook.installed,
      auditor: cliOpts.withAuditor ?? existing.components?.auditor ?? report.auditor.installed,
      rules: cliOpts.withRules ?? existing.components?.rules ?? report.rules.installed,
      watchdog: cliOpts.withWatchdog ?? existing.components?.watchdog ?? report.watchdog.installed,
    },
    setup_version: report.skill.version,
    first_run_at: existing.first_run_at || new Date().toISOString(),
    last_setup_at: new Date().toISOString(),
  };
}

function checkUpgrade(report) {
  const existing = loadUserConfig();
  const installedVer = existing.setup_version || '0.0.0';
  const currentVer = report.skill.version;
  const needsUpgrade = installedVer !== currentVer;
  return {
    installed_version: installedVer,
    current_version: currentVer,
    is_upgrade: needsUpgrade,
    stale_components: needsUpgrade ? [
      ...(existing.components?.rules ? ['rules'] : []),
      ...(existing.components?.watchdog ? ['watchdog'] : []),
    ] : [],
  };
}

async function detect() {
  const skillLane = detectSkillLane();
  const ompVersion = o.readOmpVersion();
  const ompCompat = o.checkOmpCompatibility(ompVersion, o.readOmpCompatibility());
  const detection = o.detect();

  return {
    skill: {
      lane: skillLane.lane,
      path: skillLane.path,
      version: o.readLocalVersion(),
    },
    omp: {
      version: ompVersion,
      compatibility: ompCompat,
    },
    native: {
      root: detection.native_agent_root,
      root_nonempty: detection.root_nonempty,
    },
    hook: {
      installed: detection.hook.installed,
      source: detection.hook.source,
      target: detection.hook.target,
    },
    auditor: {
      installed: detection.auditor.installed,
      source: detection.auditor.source,
      target: detection.auditor.target,
    },
    rules: detectRules(),
    watchdog: detectWatchdog(),
    omp_config: detectOmpConfig(),
    gates_selftest: await detectGatesSelfTest(),
  };
}

function planActions(report, opts) {
  const actions = [];

  if (!report.native.root_nonempty) {
    actions.push({
      type: 'warning',
      message: `native agent root (${report.native.root}) is empty or missing; OMP may not discover hooks/agents/rules.`,
    });
  }

  if (opts.upgrade) { opts.force = true; opts.apply = true; }
  if (opts.apply) {
    if (opts.withHook && !report.hook.installed) {
      actions.push({ type: 'install-hook', target: report.hook.target });
    }
    if (opts.withAuditor && !report.auditor.installed) {
      actions.push({ type: 'install-auditor', target: report.auditor.target });
    }
    if (opts.withRules && !report.rules.installed) {
      actions.push({ type: 'install-rules', target: report.rules.target, files: report.rules.files });
    }
    if (opts.withWatchdog && !report.watchdog.installed) {
      actions.push({ type: 'install-watchdog', target: report.watchdog.target });
    }
  }

  const missingConfig = Object.entries(report.omp_config.checks)
    .filter(([, v]) => !v)
    .map(([k]) => k);
  if (missingConfig.length > 0) {
    actions.push({
      type: 'config-suggestion',
      message: `OMP config.yml missing recommended keys: ${missingConfig.join(', ')}`,
      keys: missingConfig,
    });
  }

  if (report.omp.compatibility.compatible === false) {
    actions.push({
      type: 'warning',
      message: report.omp.compatibility.reason,
    });
  }

  return actions;
}

function installRules(report, force = false) {
  const targetDir = report.rules.target;
  fs.mkdirSync(targetDir, { recursive: true });
  const results = [];
  for (const f of report.rules.files) {
    const target = path.join(targetDir, f.name);
    if (fileExists(target) && !force) {
      results.push({ file: f.name, status: 'skipped', target });
      continue;
    }
    fs.copyFileSync(f.source, target);
    results.push({ file: f.name, status: 'installed', target });
  }
  return results;
}

function installWatchdog(report, force = false) {
  const results = [];
  // Install WATCHDOG.md
  const mdTarget = report.watchdog.target;
  if (fileExists(mdTarget) && !force) {
    results.push({ status: 'skipped', file: 'WATCHDOG.md', target: mdTarget });
  } else {
    fs.copyFileSync(report.watchdog.source, mdTarget);
    results.push({ status: 'installed', file: 'WATCHDOG.md', target: mdTarget });
  }
  // Install WATCHDOG.yml (same --with-watchdog flag, skip if exists)
  const ymlTarget = report.watchdog.ymlTarget;
  if (fileExists(ymlTarget) && !force) {
    results.push({ status: 'skipped', file: 'WATCHDOG.yml', target: ymlTarget });
  } else {
    fs.copyFileSync(report.watchdog.ymlSource, ymlTarget);
    results.push({ status: 'installed', file: 'WATCHDOG.yml', target: ymlTarget });
  }
  return results;
}

function apply(report, opts) {
  const results = [];

  if (opts.withHook) {
    const r = o.installHook({ force: opts.force });
    results.push({ component: 'hook', ...r });
  }
  if (opts.withAuditor) {
    const r = o.installAuditor({ force: opts.force });
    results.push({ component: 'auditor', ...r });
  }
  if (opts.withRules) {
    const r = installRules(report, opts.force);
    results.push({ component: 'rules', results: r });
  }
  if (opts.withWatchdog) {
    const r = installWatchdog(report, opts.force);
    results.push({ component: 'watchdog', results: r });
  }

  const config = buildConfig(opts, report);
  saveUserConfig(config);
  results.push({ component: 'user-config', path: userConfigFile(), status: 'saved' });

  return results;
}

function formatReport(report) {
  const lines = [];
  lines.push('STDD-OMP 环境体检');
  lines.push('==================');
  lines.push('');

  lines.push(`skill lane      : ${report.skill.lane} (${report.skill.path})`);
  const upgrade = checkUpgrade(report);
  lines.push(`skill version   : ${report.skill.version || 'unknown'}${upgrade.is_upgrade ? ` (installed: ${upgrade.installed_version} → ${upgrade.current_version})` : ''}`);
  lines.push(`OMP version     : ${report.omp.version || 'unknown'}`);
  lines.push(`OMP compatible  : ${report.omp.compatibility.compatible ? 'yes' : 'no'} (${report.omp.compatibility.reason})`);
  lines.push('');

  lines.push('opt-in components');
  lines.push(`  hook      : ${report.hook.installed ? 'installed' : 'not installed'}   → ${report.hook.target}`);
  lines.push(`  auditor   : ${report.auditor.installed ? 'installed' : 'not installed'}   → ${report.auditor.target}`);
  lines.push(`  rules     : ${report.rules.installed ? 'installed' : 'not installed'}   → ${report.rules.target}`);
  lines.push(`  watchdog  : ${report.watchdog.installed ? 'installed' : 'not installed'}   → ${report.watchdog.target}`);
  lines.push(`  watchdog.yml: ${report.watchdog.ymlInstalled ? 'installed' : 'not installed'}   → ${report.watchdog.ymlTarget}`);

  lines.push('OMP config.yml checks');
  lines.push(`  file present        : ${report.omp_config.present ? 'yes' : 'no'} (${report.omp_config.config_path})`);
  for (const [k, v] of Object.entries(report.omp_config.checks)) {
    lines.push(`  ${k.padEnd(18)} : ${v ? 'yes' : 'no'}`);
  }
  lines.push('');

  lines.push(`gates.mjs self-test : ${report.gates_selftest.ok ? 'PASS' : 'FAIL'}`);
  for (const [k, v] of Object.entries(report.gates_selftest.results)) {
    lines.push(`  ${k.padEnd(18)} : ${v ? 'ok' : 'no'}`);
  }
  if (!report.gates_selftest.ok && report.gates_selftest.reasons.length > 0) {
    for (const r of report.gates_selftest.reasons) {
      lines.push(`  ! ${r}`);
    }
  }
  lines.push('');

  if (!report.native.root_nonempty) {
    lines.push('[!] native agent root is empty; OMP may not scan hooks/agents/rules.');
    lines.push('    Create it manually or run setup with --apply after creating ~/.omp/agent/config.yml.');
    lines.push('');
  }

  return lines.join('\n');
}

function formatConfigYamlSnippet(report) {
  const lines = [];
  lines.push('推荐追加到 ~/.omp/agent/config.yml 的片段：');
  lines.push('---');
  lines.push('memory:');
  lines.push('  backend: local');
  lines.push('');
  lines.push('modelRoles:');
  lines.push('  plan: anthropic/claude-sonnet-4:medium');
  lines.push('  task: openai/gpt-5.5:medium');
  lines.push('  advisor: anthropic/claude-sonnet-4:high');
  lines.push('');
  lines.push('tools:');
  lines.push('  approvalMode: write');
  lines.push('  approval:');
  lines.push('    bash: ask');
  lines.push('    edit: ask');
  lines.push('    write: ask');
  lines.push('');
  lines.push('task:');
  lines.push('  isolation:');
  lines.push('    mode: auto');
  lines.push('  async:');
  lines.push('    enabled: true');
  lines.push('---');
  lines.push('');
  lines.push('对 OMP 配置细节有疑问，调用 /skill:omp-ops。');
  return lines.join('\n');
}

function formatActions(actions) {
  if (actions.length === 0) return 'No action needed.\n';
  const lines = [];
  lines.push('建议动作：');
  for (const a of actions) {
    if (a.type === 'warning') {
      lines.push(`  [!] ${a.message}`);
    } else if (a.type.startsWith('install-')) {
      lines.push(`  [+] ${a.type} → ${a.target}`);
    } else if (a.type === 'config-suggestion') {
      lines.push(`  [cfg] ${a.message}`);
    }
  }
  lines.push('');
  return lines.join('\n');
}

function printUsage() {
  console.log(`Usage: node scripts/setup.mjs [options]

First-time setup + environment doctor for STDD-OMP.

Options:
  --apply                  Install missing opt-in components selected by --with-*.
  --upgrade                Refresh stale opt-in components after skill version upgrade.
  --force                  Overwrite existing files when applying/upgrading.
  --with-hook              Enable/install the pre-tool danger hook.
  --with-auditor           Enable/install the custom stdd-auditor agent.
  --with-rules             Enable/install STDD system rules.
  --with-watchdog          Enable/install WATCHDOG.md for Advisor.
  --approval-mode MODE     Set preferred approval mode in ~/.stdd/config.json
                           (always-ask | write | yolo). Default: write.
  --github-repo Loveacup/jz-skills Set GitHub repo for version sync.
  --json                   Output full status as JSON (machine-readable).
  --help                   Show this message.

Examples:
  node scripts/setup.mjs                    # read-only doctor
  node scripts/setup.mjs --apply            # install all recommended components
  node scripts/setup.mjs --apply --with-hook --with-watchdog --approval-mode ask
`);
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const opts = {
    apply: false,
    force: false,
    withHook: null,
    withAuditor: null,
    withRules: null,
    withWatchdog: null,
    approvalMode: null,
    githubRepo: null,
    json: false,
    upgrade: false,
    help: false,
  };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--apply') opts.apply = true;
    else if (a === '--force') opts.force = true;
    else if (a === '--upgrade') opts.upgrade = true;
    else if (a === '--with-hook') opts.withHook = true;
    else if (a === '--with-auditor') opts.withAuditor = true;
    else if (a === '--with-rules') opts.withRules = true;
    else if (a === '--with-watchdog') opts.withWatchdog = true;
    else if (a === '--approval-mode') opts.approvalMode = args[++i];
    else if (a === '--github-repo') opts.githubRepo = args[++i];
    else if (a === '--json') opts.json = true;
    else if (a === '--help' || a === '-h') opts.help = true;
  }
  return opts;
}

async function main() {
  const opts = parseArgs(process.argv);
  if (opts.help) {
    printUsage();
    process.exit(0);
  }

  const report = await detect();

  // If --apply without explicit --with-* flags, default all to true.
  if (opts.apply) {
    if (opts.withHook === null) opts.withHook = true;
    if (opts.withAuditor === null) opts.withAuditor = true;
    if (opts.withRules === null) opts.withRules = true;
    if (opts.withWatchdog === null) opts.withWatchdog = true;
  }

  const actions = planActions(report, opts);
  let applyResults = [];

  if (opts.apply) {
    applyResults = apply(report, opts);
    // Re-detect to reflect changes.
    const updated = await detect();
    report.hook = updated.hook;
    report.auditor = updated.auditor;
    report.rules = updated.rules;
    report.watchdog = updated.watchdog;
  }

  if (opts.json) {
    console.log(JSON.stringify({ report, actions, applyResults }, null, 2));
    process.exit(0);
  }

  console.log(formatReport(report));
  console.log(formatActions(actions));
  if (actions.some((a) => a.type === 'config-suggestion')) {
    console.log(formatConfigYamlSnippet(report));
  }
  if (applyResults.length > 0) {
    console.log('Apply results:');
    for (const r of applyResults) {
      if (r.results) {
        console.log(`  ${r.component}:`);
        for (const fr of r.results) {
          console.log(`    ${fr.file}: ${fr.status}`);
        }
      } else {
        const status = r.skipped ? 'skipped' : r.ok ? 'ok' : 'failed';
        console.log(`  ${r.component}: ${status} ${r.target || r.path || ''}`);
      }
    }
    console.log('');
  }

  const anyBlocking = actions.some((a) => a.type === 'warning' && !a.message.includes('behind'));
  if (anyBlocking) {
    process.exit(2);
  }
  process.exit(0);
}

main().catch((e) => {
  console.error(`Error: ${e.message}`);
  process.exit(1);
});
