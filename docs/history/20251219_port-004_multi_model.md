# port-004: Multi-Model Configuration

Agent supports runtime model selection with unified thinking effort control.

## Overview

Port the Python multi-model architecture to TypeScript. The agent currently hardcodes `openai.responses("gpt-5.1-codex-mini")`—this feature adds Gemini and Anthropic support with provider-specific thinking effort mapping.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        runAgent(prompt, options)                    │
│                              ↓                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    createModel(modelKey, thinkingEffort)    │   │
│   │                              ↓                              │   │
│   │   ┌─────────────┬─────────────────┬─────────────────────┐   │   │
│   │   │   openai    │     gemini      │     anthropic       │   │   │
│   │   │             │                 │                     │   │   │
│   │   │ openai      │   google()      │   anthropic()       │   │   │
│   │   │ .responses()│                 │                     │   │   │
│   │   │             │                 │                     │   │   │
│   │   │ reasoning   │  thinkingLevel  │   budgetTokens      │   │   │
│   │   │ Effort      │                 │   + maxTokens       │   │   │
│   │   └─────────────┴─────────────────┴─────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│                      generateText({ model, ... })                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Input                   Model Factory                    AI SDK Call
───────────                  ─────────────                    ───────────
modelKey: "openai"     →     openai.responses()         →    reasoningEffort: "high"
modelKey: "gemini"     →     google("gemini-...")       →    thinkingConfig: {...}
modelKey: "anthropic"  →     anthropic("claude-...")    →    maxTokens + thinking
thinkingEffort: "high" →     maps to provider setting   →    (varies by provider)
```

## Provider Configuration Reference

### OpenAI (Responses API)
```typescript
import { openai } from "@ai-sdk/openai";

const model = openai.responses("gpt-5.1-codex-mini", {
  reasoningEffort: "high" // "low" | "medium" | "high"
});
```

### Google Gemini
```typescript
import { google } from "@ai-sdk/google";

const model = google("gemini-2.0-flash-thinking-exp", {
  thinkingConfig: {
    thinkingBudget: 8192  // token budget for thinking
  }
});
```

### Anthropic
```typescript
import { anthropic } from "@ai-sdk/anthropic";

const model = anthropic("claude-sonnet-4-20250514", {
  thinking: { type: "enabled", budgetTokens: 4096 }
});

// Note: Anthropic requires maxTokens >= budgetTokens
// generateText call needs: maxTokens: budgetTokens + 8192
```

## Implementation

### Phase 1: Model Registry & Factory

**File:** `aisdk-port/src/models.ts` (new)

```typescript
import { openai } from "@ai-sdk/openai";
import { google } from "@ai-sdk/google";
import { anthropic } from "@ai-sdk/anthropic";
import type { LanguageModelV1 } from "ai";

export type ModelKey = "openai" | "gemini" | "anthropic";
export type ThinkingEffort = "low" | "medium" | "high" | null;

const ANTHROPIC_BUDGET: Record<string, number> = {
  low: 1024,
  medium: 4096,
  high: 16384,
};

export interface ModelConfig {
  model: LanguageModelV1;
  maxTokens?: number;  // Required for Anthropic thinking
}

export function createModel(
  modelKey: ModelKey = "openai",
  thinkingEffort: ThinkingEffort = "high"
): ModelConfig {
  switch (modelKey) {
    case "openai":
      return {
        model: openai.responses("gpt-5.1-codex-mini", {
          reasoningEffort: thinkingEffort ?? "low",
        }),
      };

    case "gemini":
      return {
        model: google("gemini-2.0-flash-thinking-exp", {
          thinkingConfig: thinkingEffort
            ? { thinkingBudget: ANTHROPIC_BUDGET[thinkingEffort] }
            : undefined,
        }),
      };

    case "anthropic": {
      if (thinkingEffort) {
        const budget = ANTHROPIC_BUDGET[thinkingEffort];
        return {
          model: anthropic("claude-sonnet-4-20250514", {
            thinking: { type: "enabled", budgetTokens: budget },
          }),
          maxTokens: budget + 8192,
        };
      }
      return { model: anthropic("claude-sonnet-4-20250514") };
    }
  }
}

export const MODEL_KEYS: ModelKey[] = ["openai", "gemini", "anthropic"];
```

**Tasks:**
- [x] Create `src/models.ts` with type definitions
- [x] Implement `createModel()` factory function
- [x] Export `ModelConfig`, `ModelKey`, `ThinkingEffort` types

### Phase 2: Update Agent

**File:** `aisdk-port/src/agent.ts` (modify)

Update `runAgent` to accept model configuration:

```typescript
import { generateText } from "ai";
import { VirtualFileSystem } from "./virtual-fs.js";
import { createFileTools } from "./tools/file-tools.js";
import { createResearchTools } from "./tools/research-tools.js";
import { createModel, ModelKey, ThinkingEffort } from "./models.js";

// ... SYSTEM_PROMPT stays the same ...

export interface AgentOptions {
  modelKey?: ModelKey;
  thinkingEffort?: ThinkingEffort;
}

export interface AgentResult {
  text: string;
  steps: number;
  files: Map<string, string>;
}

export async function runAgent(
  prompt: string,
  options: AgentOptions = {}
): Promise<AgentResult> {
  const { modelKey = "openai", thinkingEffort = "high" } = options;
  const { model, maxTokens } = createModel(modelKey, thinkingEffort);

  const fs = new VirtualFileSystem();
  const { writeFile, readFile, runShell } = createFileTools(fs);
  const { searchArxiv, getPaperSummaries, fetchPaper } = createResearchTools(fs);

  const result = await generateText({
    model,
    system: SYSTEM_PROMPT,
    prompt,
    tools: { writeFile, readFile, runShell, searchArxiv, getPaperSummaries, fetchPaper },
    maxSteps: 50,
    ...(maxTokens && { maxTokens }),
  });

  return {
    text: result.text,
    steps: result.steps.length,
    files: fs.files,
  };
}
```

**Tasks:**
- [x] Add imports from `models.ts`
- [x] Add `AgentOptions` interface
- [x] Update `runAgent` signature to accept options
- [x] Pass `maxTokens` and `providerOptions` to `generateText` when provided
- [x] Remove hardcoded `openai.responses()` import/usage

### Phase 3: Update CLI

**File:** `aisdk-port/src/cli.ts` (modify)

Add `--model` and `--thinking` flags:

```typescript
import { runAgent } from "./agent.js";
import { MODEL_KEYS, ModelKey, ThinkingEffort } from "./models.js";

function parseArgs(args: string[]): {
  prompt: string;
  modelKey: ModelKey;
  thinkingEffort: ThinkingEffort;
} {
  let modelKey: ModelKey = "openai";
  let thinkingEffort: ThinkingEffort = "high";
  const promptParts: string[] = [];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--model" || arg === "-m") {
      const value = args[++i];
      if (MODEL_KEYS.includes(value as ModelKey)) {
        modelKey = value as ModelKey;
      }
    } else if (arg === "--thinking" || arg === "-t") {
      const value = args[++i];
      if (["low", "medium", "high", "off"].includes(value)) {
        thinkingEffort = value === "off" ? null : (value as ThinkingEffort);
      }
    } else {
      promptParts.push(arg);
    }
  }

  return { prompt: promptParts.join(" "), modelKey, thinkingEffort };
}

async function main() {
  const { prompt, modelKey, thinkingEffort } = parseArgs(process.argv.slice(2));

  if (!prompt) {
    console.log("Usage: npx tsx src/cli.ts [--model openai|gemini|anthropic] [--thinking low|medium|high|off] <prompt>");
    process.exit(1);
  }

  const result = await runAgent(prompt, { modelKey, thinkingEffort });
  console.log(result.text);

  if (result.files.size > 0) {
    console.log(`\n[${result.steps} steps, ${result.files.size} files created]`);
  }
}

main().catch(console.error);
```

**Tasks:**
- [x] Add argument parsing for `--model` and `--thinking`
- [x] Pass options to `runAgent`
- [x] Update usage message

### Phase 4: Dependencies & Verification

**Tasks:**
- [x] Add `@ai-sdk/google` and `@ai-sdk/anthropic` to package.json
- [x] Run `npm install` to update dependencies
- [ ] Verify OpenAI: `npx tsx src/cli.ts --model openai "hello"` (requires OPENAI_API_KEY)
- [ ] Verify Gemini: `npx tsx src/cli.ts --model gemini "hello"` (requires GOOGLE_GENERATIVE_AI_API_KEY)
- [ ] Verify Anthropic: `npx tsx src/cli.ts --model anthropic "hello"` (requires ANTHROPIC_API_KEY)
- [ ] Test thinking levels work with each provider

**Note:** Live verification deferred—requires API keys in environment. Type-checking passes, CLI help works.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/models.ts` | Create | Model registry and factory |
| `src/agent.ts` | Modify | Accept model options |
| `src/cli.ts` | Modify | CLI argument parsing |
| `package.json` | Modify | Add provider SDKs |

## Testing Checklist

Manual verification (no unit tests needed for this feature):

```bash
# Default (OpenAI, high thinking)
npx tsx src/cli.ts "What is 2+2?"

# Explicit model selection
npx tsx src/cli.ts --model gemini "What is 2+2?"
npx tsx src/cli.ts --model anthropic "What is 2+2?"

# Thinking levels
npx tsx src/cli.ts --model openai --thinking low "Explain recursion"
npx tsx src/cli.ts --model openai --thinking off "Explain recursion"

# Research tools should work with any model
npx tsx src/cli.ts --model gemini "Search for attention mechanism papers"
```

## Rollback

If issues arise, revert to hardcoded OpenAI in `agent.ts`:
```typescript
const model = openai.responses("gpt-5.1-codex-mini");
```

## Implementation Notes

**Actual implementation differs from plan:** The AI SDK v4 provider SDKs don't accept settings as a second argument. Instead:

1. Model is created without settings: `openai.responses("gpt-5.1-codex-mini")`
2. Provider-specific settings go in `providerOptions` passed to `generateText()`
3. `ModelConfig` returns `{ model, providerOptions, maxTokens }`

Example actual code:
```typescript
case "openai":
  return {
    model: openai.responses("gpt-5.1-codex-mini"),
    providerOptions: {
      openai: { reasoningEffort: thinkingEffort ?? "low" },
    },
  };
```

## Notes

- OpenAI uses `openai.responses()` not `openai()` - this enables reasoning features
- Gemini thinking config uses `thinkingBudget` (tokens)
- Anthropic requires `maxTokens` >= `budgetTokens` when thinking is enabled
- Python uses `claude-haiku-4-5` but we use `claude-sonnet-4` for better tool use
