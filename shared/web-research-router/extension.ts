/**
 * web-research-router — 多引擎搜索总控
 *
 * 统一注册 web_search / web_fetch，底层路由到 Exa / Tavily / Brave / SearXNG。
 * 模型通过 provider 参数选择搜索引擎，SKILL 负责路由制度。
 *
 * Fallback（v3.12，2026-06-27）：
 *   - 默认调用（未显式指定 provider）按 exa → brave → searxng 自动降级。
 *   - 任一引擎抛异常或命中 0 条 → 切下一引擎，每引擎只试一次（防雪崩）。
 *   - 显式指定 provider 时禁用 fallback（尊重用户意图，向后兼容）。
 *   - Tavily 当前限流，不入自动链，仅保留为显式 provider。
 *   - SearXNG 需 SEARXNG_URL；未设置则在链中自动跳过并记录原因。
 *   - 返回 details.actualProvider / details.fallbackChain 以保证可观测。
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import Exa from "exa-js";
import { tavily } from "@tavily/core";

type SearchResult = { title: string; url: string; snippet: string };
type FallbackStep = { provider: string; ok: boolean; count: number; error?: string };

// ── Providers ────────────────────────────────────────────────

function getExaClient() {
  const key = process.env["EXA_API_KEY"];
  if (!key) throw new Error("EXA_API_KEY not set");
  return new Exa(key);
}

function getTavilyClient() {
  const key = process.env["TAVILY_API_KEY"];
  if (!key) throw new Error("TAVILY_API_KEY not set");
  return tavily({ apiKey: key });
}

async function braveSearch(query: string, count: number) {
  // v3.12: 统一为 BRAVE_API_KEY（与 profile .env / SKILL.md / config.yaml 文档一致）。
  const key = process.env["BRAVE_API_KEY"];
  if (!key) throw new Error("BRAVE_API_KEY not set");
  const url = `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}&count=${count}`;
  const res = await fetch(url, {
    headers: {
      Accept: "application/json",
      "Accept-Encoding": "gzip",
      "X-Subscription-Token": key,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Brave API ${res.status}: ${body}`);
  }
  return res.json();
}

async function searxngSearch(query: string, count: number) {
  // env-gated：未配置 SEARXNG_URL 时抛错，由 fallback 链记录为 skipped。
  const base = process.env["SEARXNG_URL"];
  if (!base) throw new Error("SEARXNG_URL not set (skipped)");
  const url = `${base.replace(/\/$/, "")}/search?q=${encodeURIComponent(query)}&format=json`;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`SearXNG ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

async function braveFetch(url: string) {
  const res = await fetch(url, {
    headers: { "User-Agent": "pi-web-research-router/1.0" },
  });
  if (!res.ok) throw new Error(`Fetch ${res.status} for ${url}`);
  const html = await res.text();
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 8000);
}

// ── Per-provider search executors（统一返回 SearchResult[]）─────────────

async function runSearch(provider: string, query: string, count: number): Promise<SearchResult[]> {
  if (provider === "exa") {
    const exa = getExaClient();
    const res = await exa.searchAndContents(query, {
      numResults: count,
      text: { maxCharacters: 500 },
    });
    return (res.results || []).map((r: any) => ({
      title: r.title || "",
      url: r.url || "",
      snippet: (r.text || "").slice(0, 500),
    }));
  }
  if (provider === "tavily") {
    const tv = getTavilyClient();
    const res = await tv.search(query, { maxResults: count, searchDepth: "basic" });
    return (res.results || []).map((r: any) => ({
      title: r.title || "",
      url: r.url || "",
      snippet: r.content || "",
    }));
  }
  if (provider === "brave") {
    const res = await braveSearch(query, count);
    const web = res.web?.results || [];
    return web.map((r: any) => ({
      title: r.title || "",
      url: r.url || "",
      snippet: r.description || "",
    }));
  }
  if (provider === "searxng") {
    const res = await searxngSearch(query, count);
    const list = res.results || [];
    return list.slice(0, count).map((r: any) => ({
      title: r.title || "",
      url: r.url || "",
      snippet: r.content || "",
    }));
  }
  throw new Error(`Unknown provider: ${provider}`);
}

// 自动 fallback 链（Tavily 限流，不入链）。
const SEARCH_FALLBACK_ORDER = ["exa", "brave", "searxng"];

// ── Extension ─────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  // ═══════════════ web_search ═══════════════
  pi.registerTool({
    name: "web_search",
    label: "Web Search",
    description: `Search the web with provider routing + automatic fallback.

**Provider routing (choose based on web-research-router skill):**
- exa: semantic/neural search — best for discovery, academic, technical, finding projects/papers
- tavily: fact search + AI extraction — best for grounding facts, news, real-time info
- brave: general web index — best for broad coverage, mainstream results, cross-validation
- searxng: self-host metasearch — last-resort fallback (requires SEARXNG_URL)

**Fallback:** 未指定 provider 时按 exa → brave → searxng 自动降级（异常或空结果即切换，每引擎试一次）。
显式指定 provider 时禁用 fallback（尊重意图）。Tavily 当前限流，仅作显式 provider。

Returns: titles, URLs, snippets, and provider metadata (含 actualProvider / fallbackChain)。`,
    parameters: Type.Object({
      query: Type.String({ description: "Search query" }),
      max_results: Type.Optional(Type.Number({ description: "Max results (1-20, default 10)" })),
      provider: Type.Optional(
        Type.Union([
          Type.Literal("exa"),
          Type.Literal("tavily"),
          Type.Literal("brave"),
          Type.Literal("searxng"),
        ], { description: "Search engine to use (显式指定将禁用 fallback)" })
      ),
    }),
    async execute(_toolCallId, params: { query: string; max_results?: number; provider?: string }, _signal, _onUpdate, _ctx) {
      const count = Math.min(params.max_results || 10, 20);
      const explicit = !!params.provider;

      // 显式 provider → 只试该引擎；否则走自动 fallback 链。
      const chain = explicit ? [params.provider as string] : SEARCH_FALLBACK_ORDER;

      const steps: FallbackStep[] = [];
      let results: SearchResult[] = [];
      let actualProvider = "";

      for (const p of chain) {
        try {
          const r = await runSearch(p, params.query, count);
          if (r.length === 0) {
            steps.push({ provider: p, ok: false, count: 0, error: "0 results" });
            continue; // 空结果视为软失败，继续 fallback（显式时 chain 只有 1 项，自然结束）
          }
          steps.push({ provider: p, ok: true, count: r.length });
          results = r;
          actualProvider = p;
          break;
        } catch (e: any) {
          steps.push({ provider: p, ok: false, count: 0, error: String(e?.message || e) });
        }
      }

      // 全部失败：返回明确错误，逐引擎列出失败原因。
      if (actualProvider === "") {
        const reasons = steps.map((s) => `  - ${s.provider}: ${s.error}`).join("\n");
        return {
          content: [
            {
              type: "text",
              text: `## web_search FAILED (query: "${params.query}")\n\n所有引擎均不可用${explicit ? "（显式 provider，未启用 fallback）" : "（已尝试 fallback 链）"}：\n${reasons}\n\n建议：检查 API key（EXA_API_KEY / BRAVE_API_KEY / SEARXNG_URL）或稍后重试。`,
            },
          ],
          details: { provider: null, query: params.query, resultCount: 0, fallbackChain: steps },
          isError: true,
        };
      }

      const formatted = results
        .map((r, i) => `**${i + 1}. ${r.title}**\n   ${r.url}\n   ${r.snippet}`)
        .join("\n\n");

      // fallback 发生时（实际引擎非链首）在输出顶部标注降级，便于模型/用户感知。
      const degraded = !explicit && actualProvider !== SEARCH_FALLBACK_ORDER[0];
      const banner = degraded
        ? `> ⚠️ fallback: ${steps.filter((s) => !s.ok).map((s) => s.provider).join(" → ")} 失败，已降级到 **${actualProvider}**\n\n`
        : "";

      return {
        content: [
          {
            type: "text",
            text: `## web_search (provider: ${actualProvider}, query: "${params.query}")\n\n${banner}${formatted || "No results."}`,
          },
        ],
        details: {
          provider: actualProvider,
          query: params.query,
          resultCount: results.length,
          results,
          fallbackChain: steps,
        },
      };
    },
  });

  // ═══════════════ web_fetch ═══════════════
  pi.registerTool({
    name: "web_fetch",
    label: "Web Fetch",
    description: `Fetch and extract content from a URL. Provider determines extraction method, with automatic fallback.

- exa: uses Exa's native content extraction (clean text)
- tavily: uses Tavily's extract endpoint (AI-parsed content)
- brave: raw HTTP fetch + HTML-to-text stripping

**Fallback:** 未指定 provider 时按 exa → brave 自动降级（异常或空内容即切换）。显式指定时禁用 fallback。`,
    parameters: Type.Object({
      url: Type.String({ description: "URL to fetch" }),
      provider: Type.Optional(
        Type.Union([
          Type.Literal("exa"),
          Type.Literal("tavily"),
          Type.Literal("brave"),
        ], { description: "Extraction provider (默认 exa；显式指定将禁用 fallback)" })
      ),
      max_characters: Type.Optional(Type.Number({ description: "Max characters to return (default 5000)" })),
    }),
    async execute(_toolCallId, params: { url: string; provider?: string; max_characters?: number }, _signal, _onUpdate, _ctx) {
      const maxChars = params.max_characters || 5000;
      const explicit = !!params.provider;
      const chain = explicit ? [params.provider as string] : ["exa", "brave"];

      const steps: FallbackStep[] = [];
      let text = "";
      let actualProvider = "";

      for (const p of chain) {
        try {
          let t = "";
          if (p === "exa") {
            const exa = getExaClient();
            const res = await exa.getContents(params.url, { text: true });
            t = (res.results?.[0]?.text || "").slice(0, maxChars);
          } else if (p === "tavily") {
            const tv = getTavilyClient();
            const res = await tv.extract(params.url);
            t = (res.content || "").slice(0, maxChars);
          } else if (p === "brave") {
            t = (await braveFetch(params.url)).slice(0, maxChars);
          }
          if (!t) {
            steps.push({ provider: p, ok: false, count: 0, error: "empty content" });
            continue;
          }
          steps.push({ provider: p, ok: true, count: t.length });
          text = t;
          actualProvider = p;
          break;
        } catch (e: any) {
          steps.push({ provider: p, ok: false, count: 0, error: String(e?.message || e) });
        }
      }

      if (actualProvider === "") {
        const reasons = steps.map((s) => `  - ${s.provider}: ${s.error}`).join("\n");
        return {
          content: [
            { type: "text", text: `## web_fetch FAILED (url: ${params.url})\n\n${reasons}` },
          ],
          details: { provider: null, url: params.url, contentLength: 0, fallbackChain: steps },
          isError: true,
        };
      }

      const degraded = !explicit && actualProvider !== "exa";
      const banner = degraded ? `> ⚠️ fallback: exa 失败，已降级到 **${actualProvider}**\n\n` : "";

      return {
        content: [
          {
            type: "text",
            text: `## web_fetch (provider: ${actualProvider}, url: ${params.url})\n\n${banner}${text || "No content extracted."}`,
          },
        ],
        details: {
          provider: actualProvider,
          url: params.url,
          contentLength: text.length,
          fallbackChain: steps,
        },
      };
    },
  });
}
