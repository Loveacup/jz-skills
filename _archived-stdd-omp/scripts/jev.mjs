#!/usr/bin/env node
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const HOSTED_URL = 'https://api.typesafe.ai/v1/systemone';
const HOSTED_MODEL = 'jev-latest';
const NATIVE_PROTOCOL = 'jev27-bare-v1';
const NATIVE_MODEL = 'autotrust/JEV-27B-VL';
const MAX_TIMEOUT_MS = 30_000;
const MAX_INPUT_BYTES = 1_000_000;
const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;

const digest = (value) => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const safeId = (value) => typeof value === 'string' && ID.test(value);
const fail = (code) => Object.assign(new Error(code), { code });

function parseFrozenAt(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return NaN;
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return NaN;
  const [date, clock] = value.split('T');
  const [year, month, day] = date.split('-').map(Number);
  const [hour, minute, second] = clock.slice(0, 8).split(':').map(Number);
  const calendar = new Date(0);
  calendar.setUTCFullYear(year, month - 1, day);
  calendar.setUTCHours(hour, minute, second, 0);
  if (calendar.getUTCFullYear() !== year || calendar.getUTCMonth() + 1 !== month || calendar.getUTCDate() !== day || hour > 23 || minute > 59 || second > 59) return NaN;
  const offset = clock.match(/([+-])(\d{2}):(\d{2})$/);
  if (offset && (Number(offset[2]) > 23 || Number(offset[3]) > 59)) return NaN;
  return time;
}

function validateProviderIdentity(input) {
  if (input.provider === 'hosted' && (input.protocol !== 'typesafe-systemone-v1' || input.model !== HOSTED_MODEL)) throw fail('hosted_configuration_mismatch');
  if (input.provider === 'self-hosted' && (input.protocol !== NATIVE_PROTOCOL || input.model !== NATIVE_MODEL)) throw fail('native_configuration_mismatch');
}

function requireFields(input, allowed) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw fail('invalid_json_input');
  if (Object.keys(input).some((key) => !allowed.includes(key))) throw fail('unknown_field');
}

const PREPARE_FIELDS = ['sampleId', 'samplePurpose', 'projectId', 'taskId', 'checkpointId', 'coordinatorId', 'contractRef', 'provider', 'protocol', 'model', 'language', 'templateVersion', 'candidateStrategyVersion', 'permission', 'baseline', 'labelReceipt', 'question', 'state', 'candidates'];
const COMMIT_FIELDS = ['sampleId', 'choiceId'];
const SHADOW_FIELDS = ['sampleId', 'permission', 'currentContext'];

function validateInput(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw fail('invalid_input');
  for (const key of ['projectId', 'taskId', 'checkpointId', 'coordinatorId', 'contractRef', 'provider', 'protocol', 'language', 'templateVersion', 'candidateStrategyVersion']) {
    if (!safeId(input[key])) throw fail(`invalid_${key}`);
  }
  if (!['synthetic_smoke', 'formal_pilot'].includes(input.samplePurpose)) throw fail('invalid_sample_purpose');
  if (!safeId(input.sampleId)) input.sampleId = randomUUID();
  if (input.provider !== 'hosted' && input.provider !== 'self-hosted') throw fail('invalid_provider');
  validateProviderIdentity(input);
  if (!input.permission || input.permission.authorized !== true || input.permission.sensitive !== false) throw fail('not_permitted');
  if (!input.baseline || !safeId(input.baseline.receiptId) || !Number.isFinite(parseFrozenAt(input.baseline.frozenAt))) throw fail('baseline_missing');
  if (!input.labelReceipt || !safeId(input.labelReceipt.receiptId) || !Number.isFinite(parseFrozenAt(input.labelReceipt.frozenAt)) || !safeId(input.labelReceipt.source) || input.labelReceipt.source === input.coordinatorId) throw fail('label_receipt_missing');
  const maxOptions = input.provider === 'hosted' ? 255 : 256;
  if (!Array.isArray(input.candidates) || input.candidates.length < 2 || input.candidates.length > maxOptions) throw fail('invalid_candidates');
  const ids = new Set();
  for (const candidate of input.candidates) {
    if (!candidate || !safeId(candidate.id) || ids.has(candidate.id) || typeof candidate.description !== 'string' || candidate.description.length > 500) throw fail('invalid_candidate');
    ids.add(candidate.id);
  }
  if (!ids.has('no-match')) throw fail('no_match_required');
  if (typeof input.question !== 'undefined' && (typeof input.question !== 'string' || input.question.length > 1000)) throw fail('invalid_question');
  if (typeof input.state !== 'string' && (!input.state || typeof input.state !== 'object')) throw fail('invalid_state');
  const encoded = JSON.stringify(input.state);
  if (Buffer.byteLength(encoded) > MAX_INPUT_BYTES) throw fail('state_too_large');
  return input;
}

function inputProjection(input) {
  return {
    projectId: input.projectId, taskId: input.taskId, checkpointId: input.checkpointId,
    coordinatorId: input.coordinatorId, contractRef: input.contractRef,
    provider: input.provider, protocol: input.protocol, model: input.model,
    samplePurpose: input.samplePurpose,
    language: input.language, templateVersion: input.templateVersion,
    candidateStrategyVersion: input.candidateStrategyVersion,
    candidates: input.candidates, state: input.state,
    question: input.question || 'Which authorized context candidate best fits the current task state?',
    baseline: input.baseline, labelReceipt: input.labelReceipt,
  };
}
function receiptMatchesSnapshot(prepared, snapshot) {
  const ids = snapshot.candidates.map(({ id }) => id);
  return prepared.project_id === snapshot.projectId
    && prepared.task_id === snapshot.taskId
    && prepared.checkpoint_id === snapshot.checkpointId
    && prepared.coordinator_id === snapshot.coordinatorId
    && prepared.contract_ref === snapshot.contractRef
    && prepared.provider === snapshot.provider
    && prepared.protocol === snapshot.protocol
    && prepared.configured_model === snapshot.model
    && prepared.sample_purpose === snapshot.samplePurpose
    && prepared.language === snapshot.language
    && prepared.template_version === snapshot.templateVersion
    && prepared.candidate_strategy_version === snapshot.candidateStrategyVersion
    && prepared.candidate_set_digest === digest(snapshot.candidates)
    && JSON.stringify(prepared.candidate_ids) === JSON.stringify(ids)
    && prepared.baseline_receipt_id === snapshot.baseline.receiptId
    && prepared.baseline_frozen_at === snapshot.baseline.frozenAt
    && prepared.label_receipt_id === snapshot.labelReceipt.receiptId
    && prepared.label_frozen_at === snapshot.labelReceipt.frozenAt
    && prepared.label_source === snapshot.labelReceipt.source;
}

function defaultReceiptPath() {
  return path.join(os.homedir(), '.stdd', 'jev', 'receipts.jsonl');
}

function privateInputPath(receiptPath, sampleId) {
  return `${path.resolve(receiptPath)}.inputs/${sampleId}.json`;
}

async function writePrivateInput(receiptPath, sampleId, snapshot) {
  const directory = path.dirname(privateInputPath(receiptPath, sampleId));
  await fs.mkdir(directory, { recursive: true, mode: 0o700 });
  try {
    await fs.chmod(directory, 0o700);
    await fs.writeFile(privateInputPath(receiptPath, sampleId), JSON.stringify(snapshot), { flag: 'wx', mode: 0o600 });
  } catch { throw fail('private_input_write_failed'); }
}

async function readPrivateInput(receiptPath, sampleId) {
  try { return JSON.parse(await fs.readFile(privateInputPath(receiptPath, sampleId), 'utf8')); }
  catch { throw fail('private_input_unavailable'); }
}

async function consumeShadowClaim(receiptPath, sampleId, startRow) {
  return withReceiptLock(receiptPath, async (rows) => {
    if (rows.some((row) => row.event === 'shadow-start' && row.sample_id === sampleId)) throw fail('claim_already_consumed');
    await appendRow(path.resolve(receiptPath), rows, { event: 'shadow-start', ...startRow });
    return rows;
  });
}


function coordinatorDelivery(input, sampleId, startedAt, inputDigest) {
  return {
    status: 'prepared', sample_id: sampleId, project_id: input.projectId,
    task_id: input.taskId, checkpoint_id: input.checkpointId,
    coordinator_id: input.coordinatorId, sample_purpose: input.samplePurpose,
    started_at: startedAt, input_digest: inputDigest,
    candidate_set_digest: digest(input.candidates),
    candidate_ids: input.candidates.map(({ id }) => id),
    question: input.question || 'Which authorized context candidate best fits the current task state?',
    state: input.state, candidates: input.candidates,
  };
}
async function writeDelivery(receiptPath, rows, input, sampleId, startedAt, inputDigest) {
  const row = {
    event: 'candidate_delivery', sample_id: sampleId,
    coordinator_id: input.coordinatorId, project_id: input.projectId,
    task_id: input.taskId, checkpoint_id: input.checkpointId,
    started_at: startedAt, input_digest: inputDigest,
    candidate_set_digest: digest(input.candidates),
  };
  await appendRow(path.resolve(receiptPath), rows, row);
}


async function withReceiptLock(receiptPath, work) {
  const target = path.resolve(receiptPath);
  await fs.mkdir(path.dirname(target), { recursive: true, mode: 0o700 });
  await fs.chmod(path.dirname(target), 0o700);
  const lockPath = `${target}.lock`;
  let lock;
  try {
    lock = await fs.open(lockPath, 'wx', 0o600);
  } catch {
    throw fail('receipt_locked');
  }
  try {
    await lock.writeFile(`${process.pid}\n`);
    await lock.sync();
    const rows = await readRows(target);
    const result = await work(rows);
    return result;
  } finally {
    await lock.close();
    await fs.unlink(lockPath).catch(() => {});
  }
}

async function readRows(target) {
  let text;
  try { text = await fs.readFile(target, 'utf8'); }
  catch (error) { if (error.code === 'ENOENT') return []; throw fail('receipt_read_failed'); }
  const rows = [];
  for (const line of text.split('\n')) {
    if (!line) continue;
    try { rows.push(JSON.parse(line)); } catch { throw fail('receipt_corrupt'); }
  }
  return rows;
}

async function appendRow(target, rows, row) {
  try {
    const handle = await fs.open(target, 'a', 0o600);
    try { await handle.write(`${JSON.stringify(row)}\n`); await handle.sync(); }
    finally { await handle.close(); }
    await fs.chmod(target, 0o600);
  } catch { throw fail('receipt_write_failed'); }
  rows.push(row);
}

function iso(now) {
  const time = new Date(now);
  if (!Number.isFinite(time.getTime())) throw fail('invalid_clock');
  return time.toISOString();
}

export async function prepare({ receiptPath = defaultReceiptPath(), input, now = Date.now }) {
  const checked = validateInput(structuredClone(input));
  const baselineTime = parseFrozenAt(checked.baseline.frozenAt);
  const labelTime = parseFrozenAt(checked.labelReceipt.frozenAt);
  const snapshot = inputProjection(checked);
  const inputDigest = digest(snapshot);
  return withReceiptLock(receiptPath, async (rows) => {
    if (rows.some((row) => row.event === 'prepare' && row.project_id === checked.projectId && row.task_id === checked.taskId)) throw fail('task_sample_limit');
    if (rows.some((row) => row.sample_id === checked.sampleId)) throw fail('sample_id_reused');
    const checkedAt = Date.parse(iso(now()));
    if (baselineTime > checkedAt || labelTime > checkedAt) throw fail('baseline_not_frozen');
    await writePrivateInput(receiptPath, checked.sampleId, snapshot);
    const startedAt = iso(now());
    const row = {
      event: 'prepare', sample_id: checked.sampleId,
      project_id: checked.projectId, task_id: checked.taskId,
      checkpoint_id: checked.checkpointId, coordinator_id: checked.coordinatorId,
      contract_ref: checked.contractRef, provider: checked.provider,
      sample_purpose: checked.samplePurpose,
      protocol: checked.protocol, configured_model: checked.model,
      language: checked.language, template_version: checked.templateVersion,
      candidate_strategy_version: checked.candidateStrategyVersion,
      candidate_ids: checked.candidates.map(({ id }) => id),
      candidate_set_digest: digest(checked.candidates), input_digest: inputDigest,
      baseline_receipt_id: checked.baseline.receiptId,
      baseline_frozen_at: checked.baseline.frozenAt,
      label_receipt_id: checked.labelReceipt.receiptId,
      label_frozen_at: checked.labelReceipt.frozenAt,
      label_source: checked.labelReceipt.source,
      started_at: startedAt, permission_authorized: true, sensitive: false,
      status: 'prepared',
    };
    await appendRow(path.resolve(receiptPath), rows, row);
    await writeDelivery(receiptPath, rows, checked, checked.sampleId, startedAt, inputDigest);
    return coordinatorDelivery(checked, checked.sampleId, startedAt, inputDigest);
  });
}

export async function commitChoice({ receiptPath = defaultReceiptPath(), sampleId, choiceId, now = Date.now }) {
  if (!safeId(sampleId) || !safeId(choiceId)) throw fail('invalid_choice');
  return withReceiptLock(receiptPath, async (rows) => {
    const prepared = rows.find((row) => row.event === 'prepare' && row.sample_id === sampleId);
    if (!prepared) throw fail('sample_not_prepared');
    const delivery = rows.find((row) => row.event === 'candidate_delivery' && row.sample_id === sampleId);
    if (!delivery || delivery.input_digest !== prepared.input_digest) throw fail('candidate_delivery_missing');
    const committedAt = iso(now());
    if (Date.parse(committedAt) < Date.parse(prepared.started_at)) throw fail('choice_before_prepare');
    if (rows.some((row) => row.event === 'commit-choice' && row.sample_id === sampleId)) throw fail('choice_already_committed');
    if (!prepared.candidate_ids.includes(choiceId)) throw fail('choice_out_of_set');
    const row = { event: 'commit-choice', sample_id: sampleId, input_digest: prepared.input_digest, choice_id: choiceId, committed_at: committedAt };
    await appendRow(path.resolve(receiptPath), rows, row);
    return { status: 'committed', sample_id: sampleId, choice_id: choiceId, committed_at: committedAt, elapsed_ms: Date.parse(committedAt) - Date.parse(prepared.started_at), input_digest: prepared.input_digest };
  });
}

function readHostedKey(env, keychainReader) {
  if (env?.JEV_TEST_API_KEY) return env.JEV_TEST_API_KEY;
  try { return keychainReader(); }
  catch { throw fail('hosted_key_unavailable'); }
}

function keychainRead() {
  try {
    return execFileSync('/usr/bin/security', ['find-generic-password', '-a', 'alexcai', '-s', 'typesafe-jev-api-key', '-w'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 3000 }).trim();
  } catch { throw fail('hosted_key_unavailable'); }
}

function validateHostedAnswer(body, expectedIds) {
  if (!body || typeof body.model !== 'string' || !/^jev-[0-9]+\.[0-9]+\.[0-9]+$/.test(body.model)) throw fail('unknown_model_identity');
  const answer = body.answers?.pick_context_file;
  if (!answer || answer.type !== 'choice' || !expectedIds.includes(answer.choice)) throw fail('invalid_choice_response');
  const probabilities = answer.probabilities;
  if (!probabilities || typeof probabilities !== 'object' || Array.isArray(probabilities) || Object.keys(probabilities).length !== expectedIds.length || expectedIds.some((id) => !Object.hasOwn(probabilities, id))) throw fail('invalid_probabilities');
  const values = expectedIds.map((id) => probabilities[id]);
  if (values.some((value) => typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) || Math.abs(values.reduce((a, b) => a + b, 0) - 1) > 0.01) throw fail('invalid_probabilities');
  if (typeof answer.confidence !== 'number' || !Number.isFinite(answer.confidence) || answer.confidence < 0 || answer.confidence > 1) throw fail('invalid_confidence');
  return { model: body.model, choice: answer.choice, probabilities, confidence: answer.confidence, usage: sanitizeUsage(body.usage) };
}

function sanitizeUsage(usage) {
  if (!usage || typeof usage !== 'object') return null;
  const out = {};
  for (const key of ['input_tokens', 'output_tokens', 'prompt_tokens', 'completion_tokens', 'total_tokens']) if (Number.isSafeInteger(usage[key]) && usage[key] >= 0) out[key] = usage[key];
  return Object.keys(out).length ? out : null;
}

function validateNativeAnswer(body, expectedIds) {
  if (!body || body.protocol !== NATIVE_PROTOCOL || body.model !== NATIVE_MODEL || !Array.isArray(body.options) || body.options.length !== expectedIds.length || body.options.some((id, i) => id !== expectedIds[i])) throw fail('native_identity_or_protocol_mismatch');
  if (!Number.isInteger(body.choice_index) || body.choice_index < 0 || body.choice_index >= expectedIds.length || body.choice !== expectedIds[body.choice_index]) throw fail('native_choice_mismatch');
  if (!Array.isArray(body.probabilities) || body.probabilities.length !== expectedIds.length) throw fail('invalid_probabilities');
  const values = body.probabilities;
  if (values.some((value) => typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) || Math.abs(values.reduce((a, b) => a + b, 0) - 1) > 0.01) throw fail('invalid_probabilities');
  return { model: body.model, protocol: body.protocol, choice: body.choice, probabilities: Object.fromEntries(expectedIds.map((id, i) => [id, values[i]])), confidence: null, usage: sanitizeUsage(body.usage) };
}

function nativeUrl(endpoint) {
  let url;
  try { url = new URL(endpoint); } catch { throw fail('invalid_native_endpoint'); }
  const allowedHost = url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.hostname === '[::1]';
  if (url.protocol !== 'http:' || !allowedHost || url.pathname !== '/v1/decide' || url.username || url.password || url.search || url.hash) throw fail('invalid_native_endpoint');
  return url.href;
}

async function requestJson({ url, body, headers, fetchImpl, timeoutMs }) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    let response;
    try { response = await fetchImpl(url, { method: 'POST', headers, body: JSON.stringify(body), signal: controller.signal, redirect: 'error' }); }
    catch { throw fail(controller.signal.aborted ? 'request_timeout' : 'request_failed'); }
    if (!response.ok) throw fail(`http_${response.status}`);
    let payload;
    try { payload = await response.json(); } catch { throw fail('invalid_json'); }
    return payload;
  } finally { clearTimeout(timer); }
}

function errorCode(error) {
  const code = error?.code;
  if (typeof code === 'string' && /^[a-z0-9_-]+$/.test(code)) return code;
  return 'shadow_failed';
}

export async function shadow({ receiptPath = defaultReceiptPath(), sampleId, permission, currentContext, endpoint = process.env.STDD_JEV_SELF_HOSTED_ENDPOINT, env = process.env, keychainReader = keychainRead, fetchImpl = fetch, timeoutMs = 10_000, now = Date.now }) {
  const claimStartedAt = iso(now());
  let requestStartedAt = null;
  let consumed = false;
  try {
    if (!safeId(sampleId)) throw fail('invalid_sample_id');
    if (!permission || permission.authorized !== true || permission.sensitive !== false) throw fail('not_permitted');
    if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > MAX_TIMEOUT_MS) throw fail('invalid_timeout');
    if (!currentContext || !safeId(currentContext.contractRef) || typeof currentContext.inputDigest !== 'string' || !/^[a-f0-9]{64}$/.test(currentContext.inputDigest)) throw fail('invalid_current_context');
    const { prepared, committed } = await withReceiptLock(receiptPath, async (stored) => {
      const item = stored.find((row) => row.event === 'prepare' && row.sample_id === sampleId);
      const choice = stored.find((row) => row.event === 'commit-choice' && row.sample_id === sampleId);
      if (!item || !choice) throw fail('sample_not_committed');
      if (stored.some((row) => row.event === 'shadow-start' && row.sample_id === sampleId)) throw fail('claim_already_consumed');
      return { prepared: item, committed: choice };
    });
    if (prepared.permission_authorized !== true || prepared.sensitive !== false || !prepared.baseline_receipt_id || !prepared.label_receipt_id) throw fail('sample_not_eligible');
    if (currentContext.contractRef !== prepared.contract_ref || currentContext.inputDigest !== prepared.input_digest) throw fail('stale_context');
    const snapshot = await readPrivateInput(receiptPath, sampleId);
    const expectedInputDigest = digest(snapshot);
    if (expectedInputDigest !== prepared.input_digest || committed.input_digest !== prepared.input_digest || !receiptMatchesSnapshot(prepared, snapshot)) throw fail('stale_input');
    const claim = { sample_id: sampleId, input_digest: prepared.input_digest, provider: prepared.provider, claim_started_at: claimStartedAt };
    await consumeShadowClaim(receiptPath, sampleId, claim);
    consumed = true;
    const expectedIds = prepared.candidate_ids;
    let record;
    if (prepared.provider === 'hosted') {
      if (prepared.protocol !== 'typesafe-systemone-v1' || prepared.configured_model !== HOSTED_MODEL) throw fail('hosted_configuration_mismatch');
      const key = readHostedKey(env, keychainReader);
      if (!key || typeof key !== 'string') throw fail('hosted_key_unavailable');
      const criteria = Object.fromEntries(snapshot.candidates.map(({ id, description }) => [id, description]));
      requestStartedAt = iso(Date.now());
      const payload = await requestJson({
        url: HOSTED_URL, fetchImpl, timeoutMs,
        headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
        body: { state: snapshot.state, model: HOSTED_MODEL, questions: { pick_context_file: { type: 'choice', instructions: snapshot.question || 'Which authorized context candidate best fits the current task state?', criteria } } },
      });
      record = validateHostedAnswer(payload, expectedIds);
      record.provider = 'hosted'; record.protocol = 'typesafe-systemone-v1';
    } else if (prepared.provider === 'self-hosted') {
      if (prepared.protocol !== NATIVE_PROTOCOL || prepared.configured_model !== NATIVE_MODEL) throw fail('native_configuration_mismatch');
      const url = nativeUrl(endpoint);
      requestStartedAt = iso(Date.now());
      const payload = await requestJson({
        url, fetchImpl, timeoutMs, headers: { 'Content-Type': 'application/json' },
        body: { kind: 'choice', state: { context: snapshot.state, candidates: snapshot.candidates.map(({ id, description }) => ({ id, description })) }, question: snapshot.question || 'Which authorized context candidate best fits the current task state?', options: expectedIds },
      });
      record = validateNativeAnswer(payload, expectedIds);
      record.provider = 'self-hosted';
    } else throw fail('invalid_provider');
    record.status = 'shadowed';
    record.sample_id = sampleId;
    record.input_digest = prepared.input_digest;
    record.coordinator_choice = committed.choice_id;
    record.request_started_at = requestStartedAt;
    record.request_finished_at = iso(Date.now());
    record.latency_ms = Date.parse(record.request_finished_at) - Date.parse(requestStartedAt);
    record.baseline_receipt_id = prepared.baseline_receipt_id;
    record.label_receipt_id = prepared.label_receipt_id;
    await withReceiptLock(receiptPath, async (stored) => {
      if (!stored.some((row) => row.event === 'shadow-start' && row.sample_id === sampleId)) throw fail('claim_missing');
      await appendRow(path.resolve(receiptPath), stored, { event: 'shadow', ...record });
    });
    return record;
  } catch (error) {
    const status = { status: 'failed', sample_id: safeId(sampleId) ? sampleId : null, error: errorCode(error), request_started_at: requestStartedAt };
    if (!consumed) return { ...status, receipt_written: false };
    try {
      await withReceiptLock(receiptPath, async (rows) => {
        if (rows.some((row) => row.event === 'shadow' && row.sample_id === sampleId)) throw fail('claim_already_consumed');
        await appendRow(path.resolve(receiptPath), rows, { event: 'shadow', ...status, request_finished_at: iso(Date.now()) });
      });
      status.receipt_written = true;
    } catch (writeError) {
      status.receipt_written = false;
      status.receipt_error = errorCode(writeError);
    }
    return status;
  }
}

async function readStdin() {
  const chunks = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    size += chunk.length;
    if (size > MAX_INPUT_BYTES) throw fail('stdin_too_large');
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw fail('invalid_json_input'); }
}

function parseCli(argv) {
  const [command, ...args] = argv;
  if (args.length !== 0) return { command, invalid: 'unknown_argument' };
  return { command };
}

async function main() {
  const cli = parseCli(process.argv.slice(2));
  if (!['prepare', 'commit-choice', 'shadow'].includes(cli.command) || cli.invalid) throw fail(cli.invalid || 'usage');
  const input = await readStdin();
  let output;
  if (cli.command === 'prepare') {
    requireFields(input, PREPARE_FIELDS);
    output = await prepare({ input });
  } else if (cli.command === 'commit-choice') {
    requireFields(input, COMMIT_FIELDS);
    output = await commitChoice({ sampleId: input.sampleId, choiceId: input.choiceId });
  } else {
    requireFields(input, SHADOW_FIELDS);
    output = await shadow({ sampleId: input.sampleId, permission: input.permission, currentContext: input.currentContext, endpoint: process.env.STDD_JEV_SELF_HOSTED_ENDPOINT, env: {} });
  }
  process.stdout.write(`${JSON.stringify(output)}\n`);
}

function isMainModule() {
  return process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
}

if (isMainModule()) main().catch((error) => {
  process.stderr.write(`${JSON.stringify({ status: 'error', error: errorCode(error) })}\n`);
  process.exitCode = 2;
});
