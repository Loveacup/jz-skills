/**
 * web-research-router — 多引擎搜索总控
 *
 * 统一注册 web_search / web_fetch，底层路由到 Exa / Tavily / Brave。
 * 模型通过 provider 参数选择搜索引擎，SKILL 负责路由制度。
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import Exa from "exa-js";
import { tavily } from "@tavily/core";

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
  const key = process.env["BRAVE_SEARCH_API_KEY"];
  if (!key) throw new Error("BRAVE_SEARCH_API_KEY not set");
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

async function braveFetch(url: string) {
  const res = await fetch(url, {
    headers: { "User-Agent": "pi-web-research-router/1.0" },
  });
  if (!res.ok) throw new Error(`Fetch ${res.status} for ${url}`);
  const html = await res.text();
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 8000);
}

// ── Extension ─────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  // ═══════════════ web_search ═══════════════
  pi.registerTool({
    name: "web_search",
    label: "Web Search",
    description: `Search the web with provider routing.

**Provider routing (choose based on web-research-router skill):**
- exa: semantic/neural search — best for discovery, academic, technical, finding projects/papers
- tavily: fact search + AI extraction — best for grounding facts, news, real-time info
- brave: general web index — best for broad coverage, mainstream results, cross-validation

Returns: titles, URLs, snippets, and provider metadata.`,
    parameters: Type.Object({
      query: Type.String({ description: "Search query" }),
      max_results: Type.Optional(Type.Number({ description: "Max results (1-20, default 10)" })),
      provider: Type.Optional(
        Type.Union([
          Type.Literal("exa"),
          Type.Literal("tavily"),
          Type.Literal("brave"),
        ], { description: "Search engine to use (see provider routing guidance)" })
      ),
    }),
    async execute(_toolCallId, params: { query: string; max_results?: number; provider?: string }, _signal, _onUpdate, _ctx) {
      const provider = params.provider || "exa";
      const count = Math.min(params.max_results || 10, 20);

      let results: Array<{ title: string; url: string; snippet: string }> = [];

      if (provider === "exa") {
        const exa = getExaClient();
        const res = await exa.searchAndContents(params.query, {
          numResults: count,
          text: { maxCharacters: 500 },
        });
        results = (res.results || []).map((r: any) => ({
          title: r.title || "",
          url: r.url || "",
          snippet: (r.text || "").slice(0, 500),
        }));
      } else if (provider === "tavily") {
        const tv = getTavilyClient();
        const res = await tv.search(params.query, {
          maxResults: count,
          searchDepth: "basic",
        });
        results = (res.results || []).map((r: any) => ({
          title: r.title || "",
          url: r.url || "",
          snippet: r.content || "",
        }));
      } else if (provider === "brave") {
        const res = await braveSearch(params.query, count);
        const web = res.web?.results || [];
        results = web.map((r: any) => ({
          title: r.title || "",
          url: r.url || "",
          snippet: r.description || "",
        }));
      }

      const formatted = results
        .map((r, i) => `**${i + 1}. ${r.title}**\n   ${r.url}\n   ${r.snippet}`)
        .join("\n\n");

      return {
        content: [
          {
            type: "text",
            text: `## web_search (provider: ${provider}, query: "${params.query}")\n\n${formatted || "No results."}`,
          },
        ],
        details: {
          provider,
          query: params.query,
          resultCount: results.length,
          results,
        },
      };
    },
  });

  // ═══════════════ web_fetch ═══════════════
  pi.registerTool({
    name: "web_fetch",
    label: "Web Fetch",
    description: `Fetch and extract content from a URL. Provider determines extraction method.

- exa: uses Exa's native content extraction (clean text)
- tavily: uses Tavily's extract endpoint (AI-parsed content)
- brave: raw HTTP fetch + HTML-to-text stripping`,
    parameters: Type.Object({
      url: Type.String({ description: "URL to fetch" }),
      provider: Type.Optional(
        Type.Union([
          Type.Literal("exa"),
          Type.Literal("tavily"),
          Type.Literal("brave"),
        ], { description: "Extraction provider (default: exa)" })
      ),
      max_characters: Type.Optional(Type.Number({ description: "Max characters to return (default 5000)" })),
    }),
    async execute(_toolCallId, params: { url: string; provider?: string; max_characters?: number }, _signal, _onUpdate, _ctx) {
      const provider = params.provider || "exa";
      const maxChars = params.max_characters || 5000;
      let text = "";

      if (provider === "exa") {
        const exa = getExaClient();
        const res = await exa.getContents(params.url, { text: true });
        text = (res.results?.[0]?.text || "").slice(0, maxChars);
      } else if (provider === "tavily") {
        const tv = getTavilyClient();
        const res = await tv.extract(params.url);
        text = (res.content || "").slice(0, maxChars);
      } else if (provider === "brave") {
        text = (await braveFetch(params.url)).slice(0, maxChars);
      }

      return {
        content: [
          {
            type: "text",
            text: `## web_fetch (provider: ${provider}, url: ${params.url})\n\n${text || "No content extracted."}`,
          },
        ],
        details: {
          provider,
          url: params.url,
          contentLength: text.length,
        },
      };
    },
  });
}
