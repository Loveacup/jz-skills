#!/usr/bin/env node
/**
 * STDD-OMP objective gates — cross-OS, shell-free where possible.
 *
 * Primary invocation inside OMP: `eval` js (Bun VM) importing this module.
 * CLI fallback: `bun scripts/gates.mjs ...` or `node scripts/gates.mjs ...`
 *
 * Exit codes:
 *   0  PASS / clean / within limit
 *   1  FAIL (artifact missing/empty, test non-zero exit)
 *   10 DANGER pattern matched
 *   20 COUNTER exceeded hard cap
 */
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

/**
 * Single source of canonical danger patterns.
 * `assets/stdd-gate.hook.ts` embeds this list verbatim.
 * `references/gates.md` documents it as the authoritative set.
 */
export const DANGER_PATTERNS = [
  /rm\s+-\w*[rf]/i,
  /dd\s+if=/i,
  /mkfs/i,
  /\b(shutdown|reboot|halt|poweroff)\b/i,
  /\b(kill|pkill|killall)\b/i,
  /\/etc\/(passwd|shadow)|>\s*\/etc\//i,
  /\bgit\s+push\b/i,
  /\bgit\s+commit\b/i,
  /\b(npm|pnpm|yarn)\s+publish\b/i,
  /\bcargo\s+publish\b/i,
  /docker\s+.*\bpush\b/i,
  /(curl|wget)\b.*\|\s*(sh|bash)/i,
];

function stateDir() {
  return process.env.STDD_STATE_DIR || '.stdd';
}

function counterFile(key, kind) {
  const dir = path.join(stateDir(), 'counters');
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, `${key}-${kind}`);
}

function readCount(file) {
  try {
    const raw = fs.readFileSync(file, 'utf8').trim();
    const n = Number(raw);
    return Number.isFinite(n) ? Math.max(0, n) : 0;
  } catch {
    return 0;
  }
}

function writeCount(file, n) {
  fs.writeFileSync(file, String(n), 'utf8');
}

/**
 * Quote-aware argv splitter for `shell:false` cross-OS execution.
 * Handles double/single quotes; does NOT treat backslash as an escape
 * so Windows-style paths stay literal. Users needing a literal quote can
 * switch to the other quote style (e.g. "it's" or 'say "hi"').
 * Example: `node -e "process.exit(0)"` -> ['node', '-e', 'process.exit(0)']
 */
export function parseArgv(input) {
  const args = [];
  let i = 0;
  while (i < input.length) {
    while (i < input.length && /\s/.test(input[i])) i++;
    if (i >= input.length) break;

    let quote = null;
    if (input[i] === '"' || input[i] === "'") {
      quote = input[i];
      i++;
    }

    let arg = '';
    while (i < input.length) {
      const ch = input[i];
      if (quote && ch === quote) {
        i++;
        quote = null;
        break;
      }
      if (!quote && /\s/.test(ch)) break;
      arg += ch;
      i++;
    }
    args.push(arg);
  }
  return args;
}

export function verifyArtifact(filePath) {
  try {
    const st = fs.statSync(filePath);
    if (!st.isFile() || st.size === 0) {
      return { ok: false, code: 1, reason: `artifact not a non-empty file: ${filePath}` };
    }
    return { ok: true, code: 0, size: st.size };
  } catch (e) {
    return { ok: false, code: 1, reason: `artifact missing or unreadable: ${filePath}: ${e.message}` };
  }
}

export function verifyTest(cmd, { shell = false, timeout = 120000 } = {}) {
  return new Promise((resolve) => {
    let child;
    if (shell) {
      const command = Array.isArray(cmd) ? cmd.join(' ') : cmd;
      child = spawn(command, {
        shell: true,
        stdio: ['ignore', 'pipe', 'pipe'],
        timeout,
      });
    } else {
      const argv = Array.isArray(cmd) ? cmd : parseArgv(cmd);
      if (argv.length === 0) {
        resolve({ ok: false, code: 1, reason: 'empty command' });
        return;
      }
      child = spawn(argv[0], argv.slice(1), {
        shell: false,
        stdio: ['ignore', 'pipe', 'pipe'],
        timeout,
      });
    }

    const out = [];
    const err = [];
    child.stdout?.on('data', (d) => out.push(d));
    child.stderr?.on('data', (d) => err.push(d));

    child.on('error', (e) => {
      resolve({ ok: false, code: 1, reason: `spawn error: ${e.message}` });
    });

    child.on('close', (code, signal) => {
      const ok = code === 0;
      resolve({
        ok,
        code: ok ? 0 : 1,
        rawExit: code,
        signal,
        stdout: Buffer.concat(out).toString('utf8'),
        stderr: Buffer.concat(err).toString('utf8'),
      });
    });
  });
}

export function scanDanger(text) {
  const matches = [];
  for (const pattern of DANGER_PATTERNS) {
    const m = text.match(pattern);
    if (m) {
      matches.push({ pattern: pattern.source, matched: m[0] });
    }
  }
  return { ok: matches.length === 0, code: matches.length === 0 ? 0 : 10, matches };
}

export function bumpCounter({ key, kind, max, action = 'incr' }) {
  const file = counterFile(key, kind);
  let count = readCount(file);

  if (action === 'reset') {
    writeCount(file, 0);
    return { ok: true, code: 0, count: 0, max };
  }

  if (action === 'incr') {
    count += 1;
    writeCount(file, count);
    const ok = count <= max;
    return { ok, code: ok ? 0 : 20, count, max };
  }

  if (action === 'get') {
    return { ok: count <= max, code: count <= max ? 0 : 20, count, max };
  }

  return { ok: false, code: 1, reason: `unknown counter action: ${action}` };
}

function die(code, msg) {
  if (msg) process.stderr.write(`${msg}\n`);
  process.exit(code);
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const opts = {};
  const positional = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--artifact') opts.artifact = args[++i];
    else if (a === '--test') opts.test = args[++i];
    else if (a === '--shell') opts.shell = true;
    else if (a === '--command') opts.commandText = args[++i];
    else if (a === '--diff') opts.diff = args[++i];
    else if (a === '--key') opts.key = args[++i];
    else if (a === '--kind') opts.kind = args[++i];
    else if (a === '--max') opts.max = Number(args[++i]);
    else if (a === '--incr') opts.action = 'incr';
    else if (a === '--reset') opts.action = 'reset';
    else if (a === '--get') opts.action = 'get';
    else if (!a.startsWith('-')) positional.push(a);
    else die(1, `unknown option: ${a}`);
  }
  return opts;
}

async function main() {
  const opts = parseArgs(process.argv);
  const cmd = process.argv.length > 2 ? process.argv[2] : null;

  if (cmd === 'verify') {
    if (opts.artifact) {
      const r = verifyArtifact(opts.artifact);
      if (!r.ok) die(1, r.reason);
      console.log(`PASS artifact ${opts.artifact} (${r.size} bytes)`);
    }
    if (opts.test) {
      const r = await verifyTest(opts.test, { shell: opts.shell });
      if (!r.ok) die(1, `test failed (exit ${r.rawExit}${r.signal ? '/' + r.signal : ''}): ${r.stderr || r.stdout || r.reason || ''}`.trim());
      console.log(`PASS test: ${opts.test}`);
    }
    if (!opts.artifact && !opts.test) die(1, 'verify requires --artifact or --test');
    process.exit(0);
  }

  if (cmd === 'danger') {
    let text = '';
    if (opts.commandText) text = opts.commandText;
    else if (opts.diff) text = fs.readFileSync(opts.diff, 'utf8');
    else die(1, 'danger requires --command or --diff');

    const r = scanDanger(text);
    if (!r.ok) {
      const details = r.matches.map(m => `${m.matched} (pattern: ${m.pattern})`).join('; ');
      die(10, `DANGER matched: ${details}`);
    }
    console.log('CLEAN');
    process.exit(0);
  }

  if (cmd === 'counter') {
    if (!opts.key || !opts.kind) die(1, 'counter requires --key and --kind');
    const max = Number.isFinite(opts.max) ? opts.max : (opts.kind === 'slice' ? 2 : 3);
    const r = bumpCounter({ key: opts.key, kind: opts.kind, max, action: opts.action || 'incr' });
    console.log(`counter ${opts.key}-${opts.kind}: ${r.count}/${r.max}`);
    if (!r.ok) die(20, `counter exceeded max ${r.max}`);
    process.exit(0);
  }

  die(1, `unknown command: ${cmd || '(none)'}. Use: verify | danger | counter`);
}

import { pathToFileURL } from 'node:url';

function isMainModule() {
  try {
    return import.meta.url === pathToFileURL(process.argv[1]).href;
  } catch {
    return false;
  }
}

if (isMainModule()) {
  main().catch(e => die(1, e.message));
}
