/**
 * STDD-OMP pre-tool-call danger gate (opt-in, cross-OS).
 *
 * Install to ~/.omp/agent/hooks/pre/stdd-gate.ts
 * Requires ~/.omp/agent/ root to exist and be non-empty for discovery.
 *
 * Blocks bash/edit/write calls whose arguments match the canonical danger
 * pattern set. The pattern list below is intentionally self-contained and
 * must be kept in sync with scripts/gates.mjs DANGER_PATTERNS.
 */

interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
}

interface GateResult {
  block?: boolean;
  reason?: string;
}

// Keep in sync with scripts/gates.mjs DANGER_PATTERNS (single source).
const DANGER_PATTERNS: ReadonlyArray<RegExp> = [
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

const GATED_TOOLS: Record<string, true> = {
  bash: true,
  edit: true,
  write: true,
};

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function scanDanger(text: string): string | null {
  for (const pattern of DANGER_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      return `${match[0]} (pattern: ${pattern.source})`;
    }
  }
  return null;
}

function argsToText(args: Record<string, unknown>): string {
  const chunks: string[] = [];
  for (const value of Object.values(args)) {
    if (isString(value)) {
      chunks.push(value);
    } else if (value !== undefined && value !== null) {
      chunks.push(JSON.stringify(value));
    }
  }
  return chunks.join('\n');
}

export default function stddGate(toolCall: ToolCall): GateResult {
  if (GATED_TOOLS[toolCall.tool] !== true) {
    return {};
  }

  const text = argsToText(toolCall.args);
  const hit = scanDanger(text);
  if (hit) {
    return {
      block: true,
      reason: `STDD danger gate: ${hit}; 危险类需人工 (P6)`,
    };
  }

  return {};
}
