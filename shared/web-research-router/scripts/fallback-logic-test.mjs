// 独立验证 extension.ts 的 fallback 控制流（mock providers，不依赖 SDK）。
// 复刻 web_search execute 的核心循环逻辑。

const SEARCH_FALLBACK_ORDER = ["exa", "brave", "searxng"];

// 用 mock 行为模拟各引擎：返回数组 / 抛错 / 空数组
function makeRunSearch(behavior) {
  return async (provider) => {
    const b = behavior[provider];
    if (b === "throw") throw new Error(`${provider} API 432: rate limited`);
    if (b === "empty") return [];
    return [{ title: `${provider}-r1`, url: "u", snippet: "s" }];
  };
}

async function execute({ provider, behavior }) {
  const explicit = !!provider;
  const chain = explicit ? [provider] : SEARCH_FALLBACK_ORDER;
  const runSearch = makeRunSearch(behavior);
  const steps = [];
  let results = [];
  let actualProvider = "";
  for (const p of chain) {
    try {
      const r = await runSearch(p);
      if (r.length === 0) { steps.push({ provider: p, ok: false, error: "0 results" }); continue; }
      steps.push({ provider: p, ok: true, count: r.length });
      results = r; actualProvider = p; break;
    } catch (e) {
      steps.push({ provider: p, ok: false, error: String(e.message) });
    }
  }
  return { actualProvider, results, steps, failed: actualProvider === "" };
}

const cases = [
  { name: "正常: exa 成功 → 不降级", in: { behavior: { exa: "ok", brave: "ok", searxng: "ok" } }, expect: { actualProvider: "exa", failed: false, degraded: false } },
  { name: "exa 限流(432) → 降级 brave", in: { behavior: { exa: "throw", brave: "ok", searxng: "ok" } }, expect: { actualProvider: "brave", failed: false, degraded: true } },
  { name: "exa+brave 挂 → 降级 searxng", in: { behavior: { exa: "throw", brave: "throw", searxng: "ok" } }, expect: { actualProvider: "searxng", failed: false, degraded: true } },
  { name: "exa 空结果 → 降级 brave", in: { behavior: { exa: "empty", brave: "ok", searxng: "ok" } }, expect: { actualProvider: "brave", failed: false, degraded: true } },
  { name: "全挂(含 searxng 未配置) → 明确失败", in: { behavior: { exa: "throw", brave: "throw", searxng: "throw" } }, expect: { actualProvider: "", failed: true } },
  { name: "显式 provider=brave → 不 fallback(尊重意图)", in: { provider: "brave", behavior: { exa: "ok", brave: "throw", searxng: "ok" } }, expect: { actualProvider: "", failed: true } },
  { name: "显式 provider=exa 成功", in: { provider: "exa", behavior: { exa: "ok", brave: "ok", searxng: "ok" } }, expect: { actualProvider: "exa", failed: false } },
];

let pass = 0, fail = 0;
for (const c of cases) {
  const r = await execute(c.in);
  const degraded = !c.in.provider && r.actualProvider !== "" && r.actualProvider !== SEARCH_FALLBACK_ORDER[0];
  const okProvider = r.actualProvider === c.expect.actualProvider;
  const okFailed = r.failed === c.expect.failed;
  const okDegraded = c.expect.degraded === undefined || degraded === c.expect.degraded;
  const ok = okProvider && okFailed && okDegraded;
  console.log(`${ok ? "✅" : "❌"} ${c.name}`);
  if (!ok) {
    console.log(`   got: provider=${r.actualProvider} failed=${r.failed} degraded=${degraded}`);
    console.log(`   exp: provider=${c.expect.actualProvider} failed=${c.expect.failed} degraded=${c.expect.degraded}`);
    console.log(`   chain: ${JSON.stringify(r.steps)}`);
  }
  ok ? pass++ : fail++;
}
console.log(`\n=== ${pass}/${pass + fail} passed ===`);
process.exit(fail ? 1 : 0);
