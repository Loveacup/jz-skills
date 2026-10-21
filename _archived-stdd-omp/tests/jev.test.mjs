import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { commitChoice, prepare, shadow } from '../scripts/jev.mjs';

const NATIVE_PROTOCOL = 'jev27-bare-v1';
const NATIVE_MODEL = 'autotrust/JEV-27B-VL';

async function fixture(handler) {
  const server = http.createServer(handler);
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  return {
    endpoint: `http://127.0.0.1:${address.port}/v1/decide`,
    url: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

async function sandbox(t) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'stdd-jev-'));
  t.after(() => fs.rm(directory, { recursive: true, force: true }));
  return { receiptPath: path.join(directory, 'receipts.jsonl'), directory };
}

function input(overrides = {}) {
  return {
    sampleId: 'sample-1', projectId: 'project-1', taskId: 'task-1', checkpointId: 'checkpoint-1',
    coordinatorId: 'coordinator-1', contractRef: 'contract-r1', provider: 'self-hosted',
    protocol: NATIVE_PROTOCOL, model: NATIVE_MODEL, language: 'en', templateVersion: 'pick-context-v1',
    samplePurpose: 'synthetic_smoke',
    candidateStrategyVersion: 'path-summary-v1', permission: { authorized: true, sensitive: false },
    baseline: { receiptId: 'baseline-1', frozenAt: '2000-01-01T00:00:00.000Z' },
    labelReceipt: { receiptId: 'label-1', frozenAt: '2000-01-01T00:00:00.000Z', source: 'independent-reviewer' },
    question: 'Which context entry applies?',
    state: { task: 'synthetic state without sensitive content' },
    candidates: [
      { id: 'context-a', description: 'The first permitted context entry.' },
      { id: 'context-b', description: 'The second permitted context entry.' },
      { id: 'no-match', description: 'None of the candidates fits or evidence is insufficient.' },
    ],
    ...overrides,
  };
}

function nativeResponse(options, overrides = {}) {
  return {
    kind: 'choice', effective_kind: 'choice', options,
    probabilities: options.map((_, index) => index === 0 ? 0.75 : 0.25 / (options.length - 1)),
    choice_index: 0, choice: options[0], adaptation: 'native', protocol: NATIVE_PROTOCOL,
    model: NATIVE_MODEL, usage: { prompt_tokens: 21, completion_tokens: 1, total_tokens: 22 },
    ...overrides,
  };
}

async function committedSample(receiptPath, sample = input(), choiceId = 'context-b') {
  const prepared = await prepare({ receiptPath, input: sample, now: () => Date.parse('2000-01-01T00:00:00.000Z') });
  assert.equal(prepared.status, 'prepared');
  assert.deepEqual(prepared.candidate_ids, ['context-a', 'context-b', 'no-match']);
  const committed = await commitChoice({ receiptPath, sampleId: prepared.sample_id, choiceId, now: () => Date.parse('2000-01-01T00:00:05.000Z') });
  assert.equal(committed.elapsed_ms, 5000);
  return prepared;
}
const currentContext = (prepared, overrides = {}) => ({
  contractRef: 'contract-r1',
  inputDigest: prepared.input_digest,
  ...overrides,
});

test('prepare delivers frozen candidates to coordinator; receipt keeps state/label truth private and timing binds choice', async (t) => {
  const { receiptPath } = await sandbox(t);
  const inputValue = input({ state: { marker: 'private synthetic state' }, labelReceipt: { receiptId: 'label-receipt-only', frozenAt: '2000-01-01T00:00:00.000Z', source: 'blind-review' } });
  const prepared = await prepare({ receiptPath, input: inputValue, now: () => Date.parse('2000-01-01T00:00:00.000Z') });
  assert.equal(prepared.state.marker, 'private synthetic state');
  assert.equal(prepared.candidates.some((item) => item.id === 'no-match'), true);
  assert.equal(JSON.stringify(prepared).includes('truth'), false);
  const committed = await commitChoice({ receiptPath, sampleId: prepared.sample_id, choiceId: 'context-a', now: () => Date.parse('2000-01-01T00:00:08.000Z') });
  assert.equal(committed.elapsed_ms, 8000);
  const receipt = await fs.readFile(receiptPath, 'utf8');
  assert.equal(receipt.includes('private synthetic state'), false);
  assert.equal(receipt.includes('label-receipt-only'), true);
  assert.equal(receipt.includes('label_truth'), false);
  const privateState = await fs.readFile(`${receiptPath}.inputs/${prepared.sample_id}.json`, 'utf8');
  assert.equal(privateState.includes('private synthetic state'), true);
});

test('one formal sample per task blocks a second checkpoint even with a new sample id', async (t) => {
  const { receiptPath } = await sandbox(t);
  await prepare({ receiptPath, input: input({ samplePurpose: 'formal_pilot' }) });
  await assert.rejects(prepare({ receiptPath, input: input({ samplePurpose: 'formal_pilot', sampleId: 'sample-2', checkpointId: 'checkpoint-2' }) }), /task_sample_limit/);
});

test('choice commitment is single-use and rejects ids outside the delivered set', async (t) => {
  const { receiptPath } = await sandbox(t);
  const prepared = await prepare({ receiptPath, input: input() });
  await assert.rejects(commitChoice({ receiptPath, sampleId: prepared.sample_id, choiceId: 'unlisted-context' }), /choice_out_of_set/);
  await commitChoice({ receiptPath, sampleId: prepared.sample_id, choiceId: 'context-a' });
  await assert.rejects(commitChoice({ receiptPath, sampleId: prepared.sample_id, choiceId: 'context-b' }), /choice_already_committed/);
});

test('identical task identifiers in separate projects have independent sample limits', async (t) => {
  const { receiptPath } = await sandbox(t);
  const first = await prepare({ receiptPath, input: input({ sampleId: 'project-one-sample', projectId: 'project-one', taskId: 'shared-task' }) });
  const second = await prepare({ receiptPath, input: input({ sampleId: 'project-two-sample', projectId: 'project-two', taskId: 'shared-task' }) });
  assert.notEqual(first.sample_id, second.sample_id);
});

test('concurrent prepares cannot both consume the task-level sample allowance', async (t) => {
  const { receiptPath } = await sandbox(t);
  const attempts = await Promise.allSettled([
    prepare({ receiptPath, input: input({ sampleId: 'race-a' }) }),
    prepare({ receiptPath, input: input({ sampleId: 'race-b' }) }),
  ]);
  assert.equal(attempts.filter((item) => item.status === 'fulfilled').length, 1);
  const rejected = attempts.find((item) => item.status === 'rejected');
  assert.match(rejected.reason.message, /task_sample_limit|receipt_locked/);
});

test('unpermitted and sensitive hosted shadow attempts read no key and send no request', async (t) => {
  const { receiptPath } = await sandbox(t);
  const prepared = await committedSample(receiptPath, input({ provider: 'hosted', protocol: 'typesafe-systemone-v1', model: 'jev-latest' }));
  let keyReads = 0;
  let requests = 0;
  const result = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: false }, env: {}, keychainReader: () => { keyReads += 1; return 'never'; }, fetchImpl: async () => { requests += 1; throw new Error('unexpected'); } });
  assert.equal(result.error, 'not_permitted');
  assert.equal(keyReads, 0);
  assert.equal(requests, 0);
  const sensitive = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: true }, env: {}, keychainReader: () => { keyReads += 1; return 'never'; }, fetchImpl: async () => { requests += 1; throw new Error('unexpected'); } });
  assert.equal(sensitive.error, 'not_permitted');
  assert.equal(keyReads, 0);
  assert.equal(requests, 0);
  const unknownSensitivity = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true }, env: {}, keychainReader: () => { keyReads += 1; return 'never'; }, fetchImpl: async () => { requests += 1; throw new Error('unexpected'); } });
  assert.equal(unknownSensitivity.error, 'not_permitted');
  assert.equal(keyReads, 0);
  assert.equal(requests, 0);
});

test('Keychain failure is sanitized and prevents HTTP request', async (t) => {
  const { receiptPath } = await sandbox(t);
  const prepared = await committedSample(receiptPath, input({ provider: 'hosted', protocol: 'typesafe-systemone-v1', model: 'jev-latest' }));
  const secret = 'keychain-exception-secret';
  let requests = 0;
  const result = await shadow({
    receiptPath, sampleId: prepared.sample_id,
    permission: { authorized: true, sensitive: false }, env: {},
    keychainReader: () => { throw new Error(secret); },
    currentContext: currentContext(prepared),
    fetchImpl: async () => { requests += 1; throw new Error('unexpected network'); },
  });

  assert.equal(result.status, 'failed');
  assert.equal(result.error, 'hosted_key_unavailable');
  assert.equal(requests, 0);
  assert.equal(JSON.stringify(result).includes(secret), false);
  assert.equal((await fs.readFile(receiptPath, 'utf8')).includes(secret), false);
});

test('contract or current input digest mismatch rejects before keychain, network, or claim consumption', async (t) => {
  const { receiptPath } = await sandbox(t);
  const prepared = await committedSample(receiptPath, input({ provider: 'hosted', protocol: 'typesafe-systemone-v1', model: 'jev-latest' }));
  let keyReads = 0;
  let requests = 0;
  for (const mismatch of [
    currentContext(prepared, { contractRef: 'contract-r2' }),
    currentContext(prepared, { inputDigest: '0'.repeat(64) }),
  ]) {
    const result = await shadow({
      receiptPath, sampleId: prepared.sample_id,
      permission: { authorized: true, sensitive: false },
      currentContext: mismatch, env: {},
      keychainReader: () => { keyReads += 1; return 'never'; },
      fetchImpl: async () => { requests += 1; throw new Error('unexpected network'); },
    });
    assert.equal(result.status, 'failed');
    assert.equal(result.error, 'stale_context');
    assert.equal(result.receipt_written, false);
  }
  assert.equal(keyReads, 0);
  assert.equal(requests, 0);
  const receipt = await fs.readFile(receiptPath, 'utf8');
  assert.equal(receipt.includes('"event":"shadow-start"'), false);
});

test('native endpoint rejects non-loopback, redirects, and non-native configured identities before request', async (t) => {
  const { receiptPath } = await sandbox(t);
  const prepared = await committedSample(receiptPath);
  let requests = 0;
  const result = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: false }, currentContext: currentContext(prepared), endpoint: 'http://example.com/v1/decide', fetchImpl: async () => { requests += 1; } });
  assert.equal(result.error, 'invalid_native_endpoint');
  assert.equal(requests, 0);
});

test('native protocol accepts full aligned distributions and preserves coordinator choice without overriding it', async (t) => {
  const { receiptPath } = await sandbox(t);
  const server = await fixture(async (request, response) => {
    assert.equal(request.method, 'POST');
    assert.equal(request.headers.authorization, undefined);
    assert.equal(request.url, '/v1/decide');
    let body = '';
    for await (const part of request) body += part;
    const payload = JSON.parse(body);
    assert.deepEqual(payload.options, ['context-a', 'context-b', 'no-match']);
    assert.equal(payload.state.context.task, 'synthetic state without sensitive content');
    assert.deepEqual(payload.state.candidates, input().candidates);
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify(nativeResponse(payload.options)));
  });
  t.after(server.close);
  const prepared = await committedSample(receiptPath);
  const result = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: false }, currentContext: currentContext(prepared), endpoint: server.endpoint, env: { JEV_TEST_API_KEY: 'never-send-to-native' } });
  assert.equal(result.status, 'shadowed');
  assert.equal(result.choice, 'context-a');
  assert.equal(result.coordinator_choice, 'context-b');
  assert.equal(result.confidence, null);
  assert.equal(result.protocol, NATIVE_PROTOCOL);
});

test('native protocol rejects stale snapshot, bad probabilities, wrong protocol, and unknown model', async (t) => {
  for (const [caseName, mutate] of [
    ['stale', async (receiptPath, prepared) => {
      const file = `${receiptPath}.inputs/${prepared.sample_id}.json`;
      const original = JSON.parse(await fs.readFile(file, 'utf8'));
      original.state.task = 'changed after prepare';
      await fs.writeFile(file, JSON.stringify(original));
    }],
    ['bad probabilities', async () => {}],
    ['probability out of bounds', async () => {}],
    ['wrong protocol', async () => {}],
    ['unknown model', async () => {}],
    ['choice index mismatch', async () => {}],
  ]) {
    const { receiptPath } = await sandbox(t);
    const server = await fixture(async (_request, response) => {
      const probs = caseName === 'bad probabilities' ? [0.4, 0.4] : caseName === 'probability out of bounds' ? [1.1, -0.1, 0] : undefined;
      const protocol = caseName === 'wrong protocol' ? 'other-protocol' : undefined;
      const model = caseName === 'unknown model' ? 'other-model' : undefined;
      const choiceIndex = caseName === 'choice index mismatch' ? 1 : undefined;
      const payload = nativeResponse(['context-a', 'context-b', 'no-match'], {
        ...(probs ? { probabilities: probs } : {}), ...(protocol ? { protocol } : {}),
        ...(model ? { model } : {}), ...(choiceIndex !== undefined ? { choice_index: choiceIndex } : {}),
      });
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify(payload));
    });
    t.after(server.close);
    const prepared = await committedSample(receiptPath, input({ sampleId: `sample-${caseName.replaceAll(' ', '-')}`, taskId: `task-${caseName.replaceAll(' ', '-')}` }));
    await mutate(receiptPath, prepared);
    const result = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: false }, currentContext: currentContext(prepared), endpoint: server.endpoint });
    assert.equal(result.status, 'failed', caseName);
    if (caseName === 'stale') assert.equal(result.error, 'stale_input');
    else assert.match(result.error, /invalid_probabilities|native_identity_or_protocol_mismatch|native_choice_mismatch/);
  }
});

test('HTTP error response content and exceptions never enter result or receipt', async (t) => {
  const { receiptPath } = await sandbox(t);
  const secret = 'never-log-response-secret';
  const server = await fixture(async (_request, response) => {
    response.writeHead(503, { 'content-type': 'text/plain' });
    response.end(secret);
  });
  t.after(server.close);
  const prepared = await committedSample(receiptPath);
  const result = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: false }, currentContext: currentContext(prepared), endpoint: server.endpoint });
  assert.equal(result.status, 'failed');
  assert.equal(result.error, 'http_503');
  assert.equal(JSON.stringify(result).includes(secret), false);
  const receipt = await fs.readFile(receiptPath, 'utf8');
  assert.equal(receipt.includes(secret), false);
});

test('transport exception text is not reflected to output or receipt', async (t) => {
  const { receiptPath } = await sandbox(t);
  const secret = 'never-reflect-transport-detail';
  const server = await fixture((request) => {
    request.socket.on('error', () => {});
    request.socket.destroy(new Error(secret));
  });
  t.after(server.close);
  const prepared = await committedSample(receiptPath);
  const result = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: false }, currentContext: currentContext(prepared), endpoint: server.endpoint });
  assert.equal(result.status, 'failed');
  assert.equal(result.error, 'request_failed');
  assert.equal(JSON.stringify(result).includes(secret), false);
  assert.equal((await fs.readFile(receiptPath, 'utf8')).includes(secret), false);
});

test('CLI refuses secret-bearing arguments without echoing them', () => {
  const secret = 'never-allow-key-in-argv';
  const script = fileURLToPath(new URL('../scripts/jev.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [script, 'shadow', '--api-key', secret], { input: '', encoding: 'utf8' });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.equal(result.stderr.includes(secret), false);
});

test('CLI rejects injected paths and execution seams in JSON input', () => {
  const script = fileURLToPath(new URL('../scripts/jev.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [script, 'shadow'], {
    input: JSON.stringify({ sampleId: 'sample-1', permission: { authorized: true, sensitive: false }, currentContext: { contractRef: 'contract-r1', inputDigest: '0'.repeat(64) }, receiptPath: '/tmp/attacker.jsonl', fetchImpl: 'injected' }),
    encoding: 'utf8',
  });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.equal(result.stderr.includes('unknown_field'), true);
});

test('request timeout is finite, logged as failed and consumes the sample without retry', async (t) => {
  const { receiptPath } = await sandbox(t);
  const server = await fixture(async (_request, response) => { setTimeout(() => response.end('{}'), 200); });
  t.after(server.close);
  const prepared = await committedSample(receiptPath);
  const result = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: false }, currentContext: currentContext(prepared), endpoint: server.endpoint, timeoutMs: 20 });
  assert.equal(result.status, 'failed');
  assert.equal(result.error, 'request_timeout');
  assert.equal(result.receipt_written, true);
  const duplicate = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: false }, currentContext: currentContext(prepared), endpoint: server.endpoint });
  assert.equal(duplicate.error, 'claim_already_consumed');
});

test('hosted branch pins HTTPS TypeSafe URL, keeps key in request headers, and records real API contract fields', async (t) => {
  const { receiptPath } = await sandbox(t);
  const secret = 'fixture-only-api-key';
  const hostedInput = input({ provider: 'hosted', protocol: 'typesafe-systemone-v1', model: 'jev-latest' });
  const prepared = await committedSample(receiptPath, hostedInput);
  const server = await fixture(async (request, response) => {
    assert.equal(request.url, '/v1/systemone');
    assert.equal(request.headers.authorization, `Bearer ${secret}`);
    let raw = '';
    for await (const part of request) raw += part;
    const payload = JSON.parse(raw);
    assert.equal(payload.model, 'jev-latest');
    assert.deepEqual(Object.keys(payload.questions.pick_context_file.criteria), ['context-a', 'context-b', 'no-match']);
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify({ model: 'jev-1.13.0', answers: { pick_context_file: { type: 'choice', choice: 'context-a', probabilities: { 'context-a': 0.7, 'context-b': 0.2, 'no-match': 0.1 }, confidence: 0.55 } }, usage: { input_tokens: 12, output_tokens: 3 } }));
  });
  t.after(server.close);
  const fetchProxy = (url, options) => {
    assert.equal(url, 'https://api.typesafe.ai/v1/systemone');
    return fetch(`${server.url}/v1/systemone`, options);
  };
  const result = await shadow({ receiptPath, sampleId: prepared.sample_id, permission: { authorized: true, sensitive: false }, currentContext: currentContext(prepared), env: { JEV_TEST_API_KEY: secret }, fetchImpl: fetchProxy });
  assert.equal(result.status, 'shadowed');
  assert.equal(result.model, 'jev-1.13.0');
  assert.equal(result.confidence, 0.55);
  assert.deepEqual(result.usage, { input_tokens: 12, output_tokens: 3 });
  assert.equal(JSON.stringify(result).includes(secret), false);
  assert.equal((await fs.readFile(receiptPath, 'utf8')).includes(secret), false);
});

test('missing calibration/baseline is not prepared as an eligible Jev sample', async (t) => {
  const { receiptPath } = await sandbox(t);
  await assert.rejects(prepare({ receiptPath, input: input({ baseline: null }) }), /baseline_missing/);
  await assert.rejects(prepare({ receiptPath, input: input({ labelReceipt: null }) }), /label_receipt_missing/);
  await assert.rejects(prepare({ receiptPath, input: input({ baseline: { receiptId: 'baseline-future', frozenAt: '2000-01-01T00:00:01.000Z' } }), now: () => Date.parse('2000-01-01T00:00:00.000Z') }), /baseline_not_frozen/);
  await assert.rejects(prepare({ receiptPath, input: input({ baseline: { receiptId: 'baseline-invalid', frozenAt: '2026-13-01T00:00:00Z' } }) }), /baseline_missing/);
  await assert.rejects(prepare({ receiptPath, input: input({ candidates: input().candidates.slice(0, 2) }) }), /no_match_required/);
  await assert.rejects(prepare({ receiptPath, input: input({ samplePurpose: undefined }) }), /invalid_sample_purpose/);
  await assert.rejects(prepare({ receiptPath, input: input({ labelReceipt: { receiptId: 'label-incomplete', frozenAt: '2000-01-01', source: 'independent-reviewer' } }) }), /label_receipt_missing/);
  await assert.rejects(prepare({ receiptPath, input: input({ model: 'jev-latest' }) }), /native_configuration_mismatch/);
});

test('prepare accepts complete frozen timestamps with timezone offsets', async (t) => {
  const { receiptPath } = await sandbox(t);
  const offsetInput = input({
    baseline: { receiptId: 'baseline-offset', frozenAt: '2000-01-01T08:00:00+08:00' },
    labelReceipt: { receiptId: 'label-offset', frozenAt: '2000-01-01T08:00:00+08:00', source: 'independent-reviewer' },
  });
  const prepared = await prepare({ receiptPath, input: offsetInput, now: () => Date.parse('2000-01-01T00:00:00.000Z') });
  assert.equal(prepared.status, 'prepared');
});

test('rejected future baseline leaves the stable sample available for corrected preparation', async (t) => {
  const { receiptPath } = await sandbox(t);
  const now = () => Date.parse('2000-01-01T00:00:00.000Z');
  const futureInput = input({
    baseline: { receiptId: 'baseline-future', frozenAt: '2000-01-01T00:00:01.000Z' },
  });
  await assert.rejects(prepare({ receiptPath, input: futureInput, now }), /baseline_not_frozen/);
  await assert.rejects(fs.stat(`${receiptPath}.inputs/${futureInput.sampleId}.json`), { code: 'ENOENT' });
  const prepared = await prepare({ receiptPath, input: input(), now });
  assert.equal(prepared.sample_id, futureInput.sampleId);
  assert.deepEqual(prepared.candidate_ids, ['context-a', 'context-b', 'no-match']);
});

test('malformed native JSON records a consumed failure without changing the committed choice', async (t) => {
  const { receiptPath } = await sandbox(t);
  const prepared = await committedSample(receiptPath);
  let requests = 0;
  const server = await fixture((_request, response) => {
    requests += 1;
    response.writeHead(200, { 'Content-Type': 'application/json' });
    response.end('{invalid-json');
  });
  t.after(server.close);
  const result = await shadow({
    receiptPath, sampleId: prepared.sample_id,
    permission: { authorized: true, sensitive: false },
    currentContext: currentContext(prepared), endpoint: server.endpoint,
  });
  assert.equal(result.status, 'failed');
  assert.equal(result.error, 'invalid_json');
  assert.equal(result.receipt_written, true);
  assert.equal(requests, 1);
  const rows = (await fs.readFile(receiptPath, 'utf8')).trim().split('\n').map((row) => JSON.parse(row));
  assert.equal(rows.find((row) => row.event === 'commit-choice').choice_id, 'context-b');
  assert.equal(rows.find((row) => row.event === 'shadow').error, 'invalid_json');
});
