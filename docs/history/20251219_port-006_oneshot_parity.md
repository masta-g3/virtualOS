# port-006: One-Shot Mode Feature Parity

**Status:** Complete
**Priority:** 1
**Dependencies:** port-003 (research tools), port-004 (multi-model)

## Overview

Complete the TypeScript AI SDK port to achieve full one-shot CLI mode parity with the Python agent. **Primary focus:** Enable users to query research tools (search papers, get summaries, fetch papers) via CLI and get useful answers.

## Scope

| In Scope | Out of Scope |
|----------|--------------|
| Workspace sync (load files on startup) | TUI interactive mode |
| Thinking effort CLI flag | Session history |
| Provider-specific model settings | Streaming responses |
| Extended thinking output capture | File persistence (save to disk) |

## Current vs. Target State

```
CURRENT STATE                              TARGET STATE
─────────────────                          ────────────────
CLI Entry                                  CLI Entry
  ↓                                          ↓
parseArgs → prompt, modelKey               parseArgs → prompt, modelKey, thinkingEffort
  ↓                                          ↓
runAgent(prompt, {modelKey})               loadWorkspace("./workspace")
  ↓                                          ↓
VirtualFS() ← EMPTY                        VirtualFS() ← WITH WORKSPACE FILES
  ↓                                          ↓
createModel(modelKey)                      createModel(modelKey, thinkingEffort)
  ↓                                          ↓
generateText({model})                      generateText({model, providerOptions, maxTokens})
  ↓                                          ↓
return {text, steps, files, toolCalls}     return {text, steps, files, toolCalls, thinking}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI (src/cli.ts)                                │
│                                                                              │
│  parseArgs(argv) ──────────────────────────────────────────────────────────┐ │
│    │                                                                       │ │
│    ├── prompt: string                                                      │ │
│    ├── modelKey: "openai" | "gemini" | "anthropic"                        │ │
│    └── thinkingEffort: "low" | "medium" | "high" | null  ◄── NEW          │ │
│                                                                            │ │
│  main() ───────────────────────────────────────────────────────────────────┤ │
│    │                                                                       │ │
│    ├── 1. Parse args                                                       │ │
│    ├── 2. Load workspace into VFS  ◄── NEW                                │ │
│    ├── 3. Call runAgent(prompt, options)                                   │ │
│    └── 4. Print results (text, thinking, stats)                           │ │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          Models (src/models.ts)                              │
│                                                                              │
│  createModel(modelKey, thinkingEffort) ────────────────────────────────────┐ │
│    │                                                                       │ │
│    ├── case "openai":                                                      │ │
│    │   └── openai.responses("gpt-4o")                                     │ │
│    │       providerOptions: { openai: { reasoningEffort } }               │ │
│    │                                                                       │ │
│    ├── case "gemini":                                                      │ │
│    │   └── google("gemini-2.0-flash")                                     │ │
│    │       providerOptions: { google: { thinkingConfig } }  ◄── NEW       │ │
│    │                                                                       │ │
│    └── case "anthropic":                                                   │ │
│        └── anthropic("claude-sonnet-4-5")                                 │ │
│            providerOptions: { anthropic: { thinking } }  ◄── NEW          │ │
│            maxTokens: budget + 8192                       ◄── NEW          │ │
│                                                                            │ │
│  Returns: { model, providerOptions?, maxTokens? }                          │ │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        VirtualFS (src/virtual-fs.ts)                         │
│                                                                              │
│  loadFromDisk(basePath)  ◄── NEW                                            │
│    │                                                                        │
│    └── Recursively load files from basePath into VFS                        │
│        workspace/papers/foo.md → /home/user/papers/foo.md                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent (src/agent.ts)                               │
│                                                                              │
│  runAgent(prompt, options) ────────────────────────────────────────────────┐ │
│    │                                                                       │ │
│    ├── options.modelKey                                                    │ │
│    ├── options.thinkingEffort  ◄── NEW                                    │ │
│    └── options.fs  ◄── NEW (optional pre-populated VFS)                   │ │
│                                                                            │ │
│  Returns: AgentResult                                                      │ │
│    ├── text: string                                                        │ │
│    ├── steps: number                                                       │ │
│    ├── files: Record<string, string>                                       │ │
│    ├── toolCalls: ToolCall[]                                               │ │
│    └── thinking?: string  ◄── NEW                                         │ │
└────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow: Research Query Example

```
User: npx tsx src/cli.ts "Find papers about attention mechanisms from 2017"

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   CLI        │───▶│  runAgent    │───▶│ generateText │───▶│   LLM        │
│              │    │              │    │              │    │              │
│ prompt       │    │ tools:       │    │ system:      │    │ "I'll search │
│ modelKey     │    │ - searchArxiv│    │ SYSTEM_PROMPT│    │  for papers" │
│ thinkingEff  │    │ - getSummary │    │              │    │              │
└──────────────┘    │ - fetchPaper │    └──────────────┘    └──────┬───────┘
                    │ - readFile   │                               │
                    │ - writeFile  │                               │
                    │ - runShell   │                               ▼
                    └──────────────┘                        ┌──────────────┐
                                                           │ Tool Call:   │
                           ┌───────────────────────────────│ searchArxiv  │
                           │                               │ query: "att.."│
                           ▼                               └──────────────┘
                    ┌──────────────┐
                    │ LLMpedia DB  │───▶ Returns paper list
                    │ (PostgreSQL) │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ LLM Response │
                    │              │
                    │ "Found 5     │
                    │  papers..."  │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ CLI Output   │
                    │              │
                    │ Text + Stats │
                    └──────────────┘
```

## Implementation Plan

### Phase 1: Workspace Sync (Foundation)

Enable the agent to access files persisted between runs.

**File: `src/virtual-fs.ts`**

- [x] Add `loadFromDisk(basePath: string)` method
- [x] Recursively walk directory and load files
- [x] Map disk paths to VFS paths: `workspace/foo.md` → `/home/user/foo.md`

```typescript
// Add to VirtualFileSystem class
loadFromDisk(basePath: string): void {
  const walk = (dir: string, prefix: string) => {
    let entries: Dirent[];
    try {
      entries = readdirSync(join(basePath, dir), { withFileTypes: true });
    } catch {
      return; // Directory doesn't exist, skip
    }
    for (const entry of entries) {
      const relativePath = dir ? `${dir}/${entry.name}` : entry.name;
      const virtualPath = `${prefix}${relativePath}`;
      if (entry.isDirectory()) {
        walk(relativePath, prefix);
      } else {
        const content = readFileSync(join(basePath, relativePath), "utf-8");
        this.files.set(virtualPath, content);
      }
    }
  };
  walk("", "/home/user/");
}
```

**File: `src/cli.ts`**

- [x] Import VirtualFileSystem
- [x] Load workspace before running agent
- [x] Pass VFS to runAgent

```typescript
import { VirtualFileSystem } from "./virtual-fs.js";

async function main() {
  const { prompt, modelKey, thinkingEffort } = parseArgs(process.argv.slice(2));

  // Load workspace
  const fs = new VirtualFileSystem();
  fs.loadFromDisk("./workspace");

  const result = await runAgent(prompt, { modelKey, thinkingEffort, fs });
  // ...
}
```

**File: `src/agent.ts`**

- [x] Add `fs?: VirtualFileSystem` to AgentOptions
- [x] Use provided VFS or create new one

```typescript
export interface AgentOptions {
  modelKey?: ModelKey;
  thinkingEffort?: ThinkingEffort;
  fs?: VirtualFileSystem;
}

export async function runAgent(
  prompt: string,
  options: AgentOptions = {}
): Promise<AgentResult> {
  const { modelKey = "openai", thinkingEffort = "high", fs: providedFs } = options;
  const fs = providedFs || new VirtualFileSystem();
  // ...
}
```

---

### Phase 2: Thinking Effort CLI Flag

Add `--thinking` flag to control reasoning depth.

**File: `src/cli.ts`**

- [x] Update `parseArgs()` to extract `--thinking` flag
- [x] Accept values: `low`, `medium`, `high`, `off`
- [x] Update usage message

```typescript
import { MODEL_KEYS, ModelKey, ThinkingEffort } from "./models.js";

export function parseArgs(args: string[]): {
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
      if (["low", "medium", "high"].includes(value)) {
        thinkingEffort = value as ThinkingEffort;
      } else if (value === "off") {
        thinkingEffort = null;
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
    console.log("Usage: npx tsx src/cli.ts [options] <prompt>");
    console.log("");
    console.log("Options:");
    console.log("  -m, --model <name>     Model: openai, gemini, anthropic (default: openai)");
    console.log("  -t, --thinking <level> Thinking: low, medium, high, off (default: high)");
    process.exit(1);
  }

  const fs = new VirtualFileSystem();
  fs.loadFromDisk("./workspace");

  const result = await runAgent(prompt, { modelKey, thinkingEffort, fs });
  console.log(result.text);

  const fileCount = Object.keys(result.files).length;
  if (fileCount > 0 || result.toolCalls.length > 0) {
    console.log(`\n[${result.steps} steps, ${result.toolCalls.length} tool calls, ${fileCount} files]`);
  }
}
```

---

### Phase 3: Provider-Specific Model Settings

Wire thinking effort through to model creation.

**File: `src/models.ts`**

- [x] Export `ThinkingEffort` type
- [x] Update `createModel()` signature to accept `thinkingEffort`
- [x] Return `providerOptions` and `maxTokens` for each provider
- [x] Implement provider-specific settings

```typescript
import { openai } from "@ai-sdk/openai";
import { google } from "@ai-sdk/google";
import { anthropic } from "@ai-sdk/anthropic";

export type ModelKey = "openai" | "gemini" | "anthropic";
export type ThinkingEffort = "low" | "medium" | "high" | null;

export interface ModelConfig {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  model: any;
  providerOptions?: Record<string, unknown>;
  maxTokens?: number;
}

const THINKING_BUDGETS: Record<string, number> = {
  low: 1024,
  medium: 4096,
  high: 16384,
};

export function createModel(
  modelKey: ModelKey = "openai",
  thinkingEffort: ThinkingEffort = "high"
): ModelConfig {
  switch (modelKey) {
    case "openai":
      return {
        model: openai("gpt-4o"),
        providerOptions: thinkingEffort
          ? { openai: { reasoningEffort: thinkingEffort } }
          : undefined,
      };

    case "gemini":
      return {
        model: google("gemini-2.0-flash"),
        providerOptions: thinkingEffort
          ? { google: { thinkingConfig: { thinkingBudget: THINKING_BUDGETS[thinkingEffort] } } }
          : undefined,
      };

    case "anthropic": {
      if (thinkingEffort) {
        const budget = THINKING_BUDGETS[thinkingEffort];
        return {
          model: anthropic("claude-sonnet-4-5"),
          maxTokens: budget + 8192,
          providerOptions: {
            anthropic: { thinking: { type: "enabled", budgetTokens: budget } },
          },
        };
      }
      return { model: anthropic("claude-sonnet-4-5") };
    }
  }
}

export const MODEL_KEYS: ModelKey[] = ["openai", "gemini", "anthropic"];
```

**File: `src/agent.ts`**

- [x] Import `ThinkingEffort` from models
- [x] Pass `thinkingEffort` to `createModel()`
- [x] Spread `providerOptions` and `maxTokens` into `generateText()` call

```typescript
import { createModel, ModelKey, ThinkingEffort } from "./models.js";

export interface AgentOptions {
  modelKey?: ModelKey;
  thinkingEffort?: ThinkingEffort;
  fs?: VirtualFileSystem;
}

export async function runAgent(
  prompt: string,
  options: AgentOptions = {}
): Promise<AgentResult> {
  const { modelKey = "openai", thinkingEffort = "high", fs: providedFs } = options;
  const { model, providerOptions, maxTokens } = createModel(modelKey, thinkingEffort);

  const fs = providedFs || new VirtualFileSystem();
  const { writeFile, readFile, runShell } = createFileTools(fs);
  const { searchArxiv, getPaperSummaries, fetchPaper } = createResearchTools(fs);

  const result = await generateText({
    model,
    system: SYSTEM_PROMPT,
    prompt,
    tools: { writeFile, readFile, runShell, searchArxiv, getPaperSummaries, fetchPaper },
    stopWhen: stepCountIs(50),
    ...(providerOptions && { providerOptions }),
    ...(maxTokens && { maxTokens }),
  });

  // ... rest of function
}
```

---

### Phase 4: Extended Thinking Output (Optional Enhancement)

Capture and display thinking output from extended thinking models.

**File: `src/agent.ts`**

- [x] Add `reasoning?: string` to AgentResult
- [x] Extract reasoning from result steps
- [x] Return reasoning in result

```typescript
export interface AgentResult {
  text: string;
  steps: number;
  files: Record<string, string>;
  toolCalls: ToolCall[];
  thinking?: string;
}

export async function runAgent(...): Promise<AgentResult> {
  // ... existing code ...

  // Extract thinking if present (varies by provider)
  let thinking: string | undefined;
  if (result.experimental_providerMetadata?.anthropic?.thinking) {
    thinking = result.experimental_providerMetadata.anthropic.thinking;
  }

  return {
    text: result.text,
    steps: result.steps.length,
    files: Object.fromEntries(fs.files),
    toolCalls,
    thinking,
  };
}
```

**File: `src/cli.ts`**

- [x] Display reasoning output when present (condensed format)

```typescript
async function main() {
  // ... existing code ...

  const result = await runAgent(prompt, { modelKey, thinkingEffort, fs });

  // Show thinking (condensed) if present
  if (result.thinking) {
    const lines = result.thinking.split("\n").slice(0, 5);
    console.log("[thinking]", lines.join(" ").slice(0, 200) + "...");
    console.log("");
  }

  console.log(result.text);

  // ... stats output ...
}
```

---

### Phase 5: Testing & Verification

- [x] Test workspace loading

```bash
mkdir -p workspace/papers
echo "# Test Paper\nThis is a test." > workspace/papers/test.md
npx tsx src/cli.ts "Read the file papers/test.md"
# Expected: Agent finds and reads the file
```

- [x] Test thinking effort flag

```bash
npx tsx src/cli.ts --thinking low "What is 2+2?"
npx tsx src/cli.ts --thinking high "Explain transformer architecture"
npx tsx src/cli.ts --thinking off "List files"
```

- [x] Test research workflow (primary use case)

```bash
# Search papers
npx tsx src/cli.ts "Search for papers about attention mechanisms from 2017"

# Get summaries
npx tsx src/cli.ts "Get medium summaries for papers 1706.03762 and 1810.04805"

# Fetch and read paper
npx tsx src/cli.ts "Download and summarize the paper 1706.03762"

# Complex research query
npx tsx src/cli.ts "Find papers about RLHF, get their summaries, and create a comparison table"
```

- [x] Test multi-model (if API keys available)

```bash
npx tsx src/cli.ts --model openai "Search for vision transformer papers"
npx tsx src/cli.ts --model gemini "Search for vision transformer papers"
npx tsx src/cli.ts --model anthropic "Search for vision transformer papers"
```

---

## File Changes Summary

| File | Action | Changes |
|------|--------|---------|
| `src/virtual-fs.ts` | Modify | Add `loadFromDisk()` method |
| `src/models.ts` | Modify | Export `ThinkingEffort`, update `createModel()` signature, add provider options |
| `src/agent.ts` | Modify | Accept `thinkingEffort` and `fs` options, pass to `generateText()`, capture thinking |
| `src/cli.ts` | Modify | Add `--thinking` flag, load workspace, display thinking |

## Rollback

If issues arise, the changes are isolated to 4 files. Revert to previous commit:
```bash
git checkout HEAD~1 -- src/virtual-fs.ts src/models.ts src/agent.ts src/cli.ts
```

## Success Criteria

1. **Workspace sync works:** Files in `./workspace/` are accessible via agent file tools
2. **Thinking flag works:** `--thinking low|medium|high|off` affects model behavior
3. **Research queries work:** User can ask about papers and get answers using the tools
4. **Multi-model works:** All three providers can be selected and function

## Notes

- Provider options structure may differ from documentation—verify with actual API calls
- Extended thinking output format is experimental and may change
- Gemini/Anthropic models require separate API keys in `.env`
