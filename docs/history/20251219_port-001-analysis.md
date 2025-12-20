# AI SDK Port Analysis: Understanding the Epic & Missing Pieces

**Date:** 2025-12-19
**Status:** Analysis Complete
**Audience:** Development team

## Executive Summary

The **@aisdk-port/** epic successfully ported the core agent architecture from PydanticAI (Python) to the Vercel AI SDK (TypeScript). The **one-shot CLI mode** works for OpenAI, but the full feature parity with the Python agent is incomplete.

**Current state:** ~70% feature parity
**What's missing:** Thinking effort control, workspace sync, session history, extended thinking features

---

## What is "One-Shot Mode"?

The Python agent's CLI entry point (via `python virtual_agent.py "<prompt>"`):

1. Accepts a prompt as a command-line argument
2. Optionally loads workspace files from disk (`.load_from_disk()`)
3. Runs the agent synchronously (calls `agent.run()`)
4. Returns agent output and file stats
5. Exits

**TypeScript equivalent:** `tsx src/cli.ts "<prompt>"`

The one-shot mode is **partially working** in the TypeScript port, but lacks several critical features that the Python version has.

---

## Architecture Comparison

### Python (Original) - `virtual_agent.py`

```
CLI Entry
  ↓
parseArgs(sys.argv) → prompt, model_key, thinking_effort
  ↓
create_agent(model_key, thinking_effort)
  ├── Select model string from MODELS[model_key]
  ├── Build provider-specific settings via _build_settings()
  ├── Create Agent with system_prompt + tools
  ↓
Load workspace from disk
  ├── fs.load_from_disk(Path("./workspace"))
  ↓
Run agent
  ├── agent.run(prompt, deps=AgentDeps(fs, workspace_path))
  ├── Agents creates VirtualFileSystem with workspace files
  ↓
Output results
  ├── print(result.output)
  ├── print(f"[{steps} steps, {created_files} files]")
```

### TypeScript (Port) - `src/cli.ts`

```
CLI Entry
  ↓
parseArgs(process.argv) → prompt, modelKey (NO thinking effort)
  ↓
runAgent(prompt, { modelKey })
  ├── createModel(modelKey) → { model }
  ├── VirtualFileSystem() → empty (no workspace sync)
  ├── createFileTools(fs), createResearchTools(fs)
  ├── generateText({ model, system_prompt, tools, ... })
  ↓
Output results
  ├── console.log(result.text)
  ├── console.log(`[${steps} steps, ${toolCalls} calls, ${files} files]`)
```

---

## Detailed Feature Comparison

### ✅ Implemented Features

| Feature | Python | TypeScript | Status |
|---------|--------|-----------|--------|
| **CLI one-shot mode** | ✅ | ✅ | Working |
| **Model selection (--model)** | ✅ | ✅ | Working |
| **Virtual filesystem** | ✅ | ✅ | Working |
| **File tools** (read, write, ls, cd, rm, grep) | ✅ | ✅ | Working |
| **Research tools** (search, summaries, fetch) | ✅ | ✅ | Working |
| **OpenAI provider** | ✅ | ✅ | Working |
| **Gemini provider** | ✅ | ⚠️ | Defined, untested |
| **Anthropic provider** | ✅ | ⚠️ | Defined, untested |
| **Multi-step agent loops** | ✅ | ✅ | Working (stopWhen: stepCountIs(50)) |
| **Tool call introspection** | ✅ | ✅ | Captured in AgentResult.toolCalls |

### ❌ Missing Features

| Feature | Python | TypeScript | Impact |
|---------|--------|-----------|--------|
| **Thinking effort control** (--thinking low\|medium\|high\|off) | ✅ | ❌ | **HIGH** - Port feature incomplete |
| **Workspace sync on startup** | ✅ | ❌ | **MEDIUM** - Can't load saved files |
| **Session history** | ✅ | ❌ | **LOW** - Not critical for one-shot |
| **Provider-specific model config** | ✅ | ⚠️ | **MEDIUM** - Models hardcoded, no reasoning/thinking config |
| **Extended thinking** | ✅ (claude) | ❌ | **MEDIUM** - No Anthropic thinking output |

---

## Root Cause Analysis: Why These Are Missing

### 1. **Thinking Effort Control (--thinking flag)**

**Python implementation:**
```python
def _build_settings(model_key: str, thinking_effort: ThinkingEffort):
    if model_key == "openai":
        return OpenAIResponsesModelSettings(
            openai_reasoning_effort=thinking_effort or "none"
        )
    if model_key == "gemini":
        return GoogleModelSettings(
            google_thinking_config={"thinking_level": thinking_effort or "minimal"}
        )
    if model_key == "haiku":
        budget = ANTHROPIC_BUDGET[thinking_effort]
        return AnthropicModelSettings(
            anthropic_thinking={"type": "enabled", "budget_tokens": budget},
            max_tokens=budget + 8192
        )
```

**TypeScript current state:**
- `models.ts` has `ThinkingEffort` type defined
- `createModel()` only takes `modelKey`, not `thinkingEffort`
- CLI `parseArgs()` doesn't extract `--thinking` flag
- **Result:** Thinking effort is hardcoded to default per provider

**Missing:** CLI flag parsing + model factory update

### 2. **Workspace Sync on Startup**

**Python implementation:**
```python
# In main():
fs = VirtualFileSystem()
workspace = Path("./workspace")
fs.load_from_disk(workspace)  # ← Loads all files from disk
deps = AgentDeps(fs=fs, workspace_path=workspace)
result = await agent.run(prompt, deps=deps)
```

**TypeScript current state:**
```typescript
// In runAgent():
const fs = new VirtualFileSystem();
// ← No load_from_disk() call
const result = await generateText({ ... });
```

**Missing:**
- `VirtualFileSystem.loadFromDisk(path)` method
- Call to load workspace on CLI startup

### 3. **Session History**

**Python implementation:** TUI feature (not CLI one-shot)

**TypeScript:** Not ported—only needed for TUI, not one-shot mode

**Impact:** LOW for one-shot, but critical for eventual interactive mode

### 4. **Extended Thinking Output Visibility**

**Python:** Agents capture Claude thinking via `result.output` (includes thinking tags)

**TypeScript:** Captured tool calls but not thinking process visibility

**Impact:** MEDIUM—users won't see reasoning process

---

## Path to Full Parity: Step-by-Step

### Phase 1: Add Thinking Effort Control (PRIORITY: HIGH)

**Goal:** CLI `--thinking low|medium|high|off` flag works

**Files to modify:**

1. **`src/models.ts`** - Update `createModel()` signature:
   ```typescript
   export type ThinkingEffort = "low" | "medium" | "high" | null;

   export function createModel(
     modelKey: ModelKey = "openai",
     thinkingEffort: ThinkingEffort = "high"  // ← ADD THIS
   ): ModelConfig { ... }
   ```

2. **`src/cli.ts`** - Add `--thinking` flag parsing:
   ```typescript
   export function parseArgs(args: string[]): {
     prompt: string;
     modelKey: ModelKey;
     thinkingEffort: ThinkingEffort;  // ← ADD THIS
   } { ... }

   async function main() {
     const { prompt, modelKey, thinkingEffort } = parseArgs(...);
     const result = await runAgent(prompt, { modelKey, thinkingEffort });
   }
   ```

3. **`src/agent.ts`** - Accept and use thinking effort:
   ```typescript
   export interface AgentOptions {
     modelKey?: ModelKey;
     thinkingEffort?: ThinkingEffort;  // ← ADD THIS
   }

   export async function runAgent(
     prompt: string,
     options: AgentOptions = {}
   ): Promise<AgentResult> {
     const { modelKey = "openai", thinkingEffort = "high" } = options;  // ← UPDATE
     const { model, maxTokens, providerOptions } = createModel(modelKey, thinkingEffort);
     // Pass providerOptions to generateText
   }
   ```

**Effort:** ~2 hours
**Blockers:** Need to understand how AI SDK v5 handles provider options

**Testing:**
```bash
npx tsx src/cli.ts --thinking low "What is 2+2?"
npx tsx src/cli.ts --thinking high "Explain recursion deeply"
npx tsx src/cli.ts --thinking off "List files"
```

---

### Phase 2: Workspace Sync on Startup (PRIORITY: HIGH)

**Goal:** CLI loads `.workspace/*` files into VirtualFileSystem before running agent

**Files to modify:**

1. **`src/virtual-fs.ts`** - Add `loadFromDisk()` method:
   ```typescript
   import { readdirSync, readFileSync } from "fs";
   import { join } from "path";

   export class VirtualFileSystem {
     // ... existing code ...

     loadFromDisk(basePath: string): void {
       const walk = (dir: string, prefix: string) => {
         const entries = readdirSync(join(basePath, dir), { withFileTypes: true });
         for (const entry of entries) {
           const path = join(dir, entry.name);
           const virtualPath = `${prefix}${entry.name}`;
           if (entry.isDirectory()) {
             walk(path, `${virtualPath}/`);
           } else {
             const content = readFileSync(join(basePath, path), "utf-8");
             this.files.set(virtualPath, content);
           }
         }
       };
       walk("", "/home/user/");
     }
   }
   ```

2. **`src/cli.ts`** - Call `loadFromDisk()` on startup:
   ```typescript
   async function main() {
     const { prompt, modelKey, thinkingEffort } = parseArgs(...);

     // Create VFS and load workspace
     const fs = new VirtualFileSystem();
     fs.loadFromDisk("./workspace");  // ← ADD THIS

     const result = await runAgent(prompt, { modelKey, thinkingEffort, fs });  // ← PASS FS
   }
   ```

3. **`src/agent.ts`** - Accept optional pre-populated VFS:
   ```typescript
   export interface AgentOptions {
     modelKey?: ModelKey;
     thinkingEffort?: ThinkingEffort;
     fs?: VirtualFileSystem;  // ← ADD THIS
   }

   export async function runAgent(
     prompt: string,
     options: AgentOptions = {}
   ): Promise<AgentResult> {
     const fs = options.fs || new VirtualFileSystem();  // ← USE PROVIDED OR CREATE NEW
     // ... rest of function ...
   }
   ```

**Effort:** ~1.5 hours
**Blockers:** None
**Testing:**
```bash
mkdir -p workspace/papers
echo "# Test" > workspace/papers/test.md
npx tsx src/cli.ts "Read papers/test.md"  # Should find it
```

---

### Phase 3: Provider-Specific Settings & Model Config (PRIORITY: MEDIUM)

**Goal:** Thinking budgets, reasoning effort, max tokens applied per provider

**Current problem:** Models hardcoded without settings
```typescript
case "openai":
  return { model: openai("gpt-4o") };  // ← No reasoning_effort!
case "anthropic":
  return { model: anthropic("claude-sonnet-4-5") };  // ← No thinking config!
```

**Fix:** Return full `ModelConfig` with provider options
```typescript
export interface ModelConfig {
  model: LanguageModelV1;
  maxTokens?: number;
  providerOptions?: Record<string, unknown>;
}

function createModel(
  modelKey: ModelKey = "openai",
  thinkingEffort: ThinkingEffort = "high"
): ModelConfig {
  const BUDGETS = { low: 1024, medium: 4096, high: 16384 };

  switch (modelKey) {
    case "openai":
      return {
        model: openai.responses("gpt-5.1-codex-mini"),  // ← Use responses() for reasoning
        providerOptions: {
          openai: { reasoningEffort: thinkingEffort ?? "low" },
        },
      };
    case "gemini":
      return {
        model: google("gemini-2.0-flash-thinking-exp"),
        providerOptions: thinkingEffort ? {
          google: { thinkingConfig: { thinkingBudget: BUDGETS[thinkingEffort] } }
        } : undefined,
      };
    case "anthropic":
      if (thinkingEffort) {
        const budget = BUDGETS[thinkingEffort];
        return {
          model: anthropic("claude-sonnet-4-20250514"),
          maxTokens: budget + 8192,
          providerOptions: {
            anthropic: { thinking: { type: "enabled", budgetTokens: budget } }
          },
        };
      }
      return { model: anthropic("claude-sonnet-4-20250514") };
  }
}
```

**Effort:** ~1 hour
**Blockers:** Verify AI SDK v5 `providerOptions` structure

---

### Phase 4: Extended Thinking Output (PRIORITY: MEDIUM)

**Goal:** Display extended thinking output from Claude

**Current problem:** Only agent text is returned, not thinking process

**Fix:** Capture thinking from `result.reasoning` or `result.steps`
```typescript
export interface AgentResult {
  text: string;
  steps: number;
  files: Record<string, string>;
  toolCalls: ToolCall[];
  thinking?: string;  // ← ADD THIS for Anthropic
}

export async function runAgent(...): Promise<AgentResult> {
  const result = await generateText({ ... });

  // Anthropic may include thinking in result
  let thinking = undefined;
  if ("reasoning" in result) {
    thinking = (result as any).reasoning;
  }

  return {
    text: result.text,
    steps: result.steps.length,
    files: Object.fromEntries(fs.files),
    toolCalls,
    thinking,  // ← INCLUDE IF PRESENT
  };
}
```

**Effort:** ~1.5 hours
**Blockers:** Verify AI SDK v5 thinking output structure

---

## Implementation Priority & Timeline

| Phase | Feature | Status | Effort | Priority | Blocker? |
|-------|---------|--------|--------|----------|----------|
| 1 | Thinking effort CLI flag | 🔴 MISSING | 2h | HIGH | No |
| 2 | Workspace sync on startup | 🔴 MISSING | 1.5h | HIGH | No |
| 3 | Provider settings (reasoning, thinking config) | 🟡 PARTIAL | 1h | MEDIUM | No |
| 4 | Extended thinking output | 🔴 MISSING | 1.5h | MEDIUM | No |
| 5 | Session history (TUI feature) | 🔴 MISSING | 4h | LOW | - |

**Total for one-shot parity:** ~6 hours
**Total for full parity (including TUI):** ~10 hours

---

## Testing Checklist for Full Parity

```bash
# Phase 1: Thinking effort
npx tsx src/cli.ts --thinking low "2+2?"
npx tsx src/cli.ts --thinking high "Explain recursion"
npx tsx src/cli.ts --thinking off "List files"

# Phase 2: Workspace sync
mkdir -p workspace/papers
echo "# Saved notes" > workspace/notes.md
npx tsx src/cli.ts "What's in notes.md?"  # Should find it

# Phase 3: Model-specific settings
npx tsx src/cli.ts --model openai --thinking high "What is AI?"
npx tsx src/cli.ts --model anthropic --thinking medium "Search for papers"
npx tsx src/cli.ts --model gemini "Explain attention"

# Phase 4: Compare outputs
# OpenAI should show reasoning_effort
# Anthropic should show thinking budget
# All should match Python behavior

# Research tools
npx tsx src/cli.ts "Search for transformer papers from 2017"
npx tsx src/cli.ts "Get summaries for papers: 1706.03762 1810.04805"
```

---

## Known Gaps in Implementation

### 1. **Model Strings Don't Match Python**

| Feature | Python | TypeScript |
|---------|--------|-----------|
| OpenAI | `"openai-responses:gpt-5.1-codex-mini"` | `openai("gpt-4o")` |
| Gemini | `"google-gla:gemini-3-flash-preview"` | `google("gemini-2.0-flash")` |
| Anthropic | `"anthropic:claude-haiku-4-5"` | `anthropic("claude-sonnet-4-5")` |

**Impact:** TypeScript uses different models (older in some cases). Not a blocking issue but inconsistent.

### 2. **Provider Settings Structure Unknown in AI SDK v5**

The exact structure for `providerOptions` in AI SDK v5's `generateText()` is unclear. Needs verification via:
- Checking AI SDK v5 types
- Running test queries
- Reading Vercel AI SDK documentation

### 3. **Extended Thinking Output Structure**

How Anthropic/Gemini thinking appears in `generateText()` result is unclear. Needs investigation.

### 4. **VirtualFileSystem Uses Map vs Record**

- Python: dict
- TypeScript: Map (internal), Record (exported)
- AI SDK API: expects plain objects

This causes `Object.fromEntries(fs.files)` in return value. Map should be preserved internally for consistency.

---

## Recommendations

### Immediate Actions (This Sprint)

1. **Phase 1 + Phase 2:** Add thinking effort flag and workspace sync
   - These are straightforward additions
   - Unblock one-shot mode feature parity
   - ~3.5 hours total

2. **Update documentation:**
   - Update STRUCTURE.md with TypeScript CLI usage
   - Document `--thinking` flag in CLI help
   - Add workspace sync instructions

### Follow-up Work (Next Sprint)

1. **Phase 3 + 4:** Provider settings and extended thinking
   - Requires AI SDK investigation
   - Less critical but improves feature parity

2. **Model selection verification:**
   - Test all three models (OpenAI, Gemini, Anthropic)
   - Ensure thinking/reasoning works as expected
   - May require API key setup in CI/CD

### Long-term (Future Epics)

1. **Session history:** Needed for TUI parity
2. **Interactive mode:** Chat loop, not just one-shot
3. **File persistence:** Save/load agent conversations

---

## Summary Table: What's Working vs. What's Missing

```
┌─────────────────────────────────────────────────────────────────┐
│                  ONE-SHOT MODE FEATURE MATRIX                   │
├─────────────────────────────────────────────┬──────────┬────────┤
│ Feature                                     │ Python   │ TS     │
├─────────────────────────────────────────────┼──────────┼────────┤
│ CLI one-shot execution                      │ ✅      │ ✅    │
│ Prompt from command-line arg                │ ✅      │ ✅    │
│ Model selection (--model)                   │ ✅      │ ✅    │
│ Thinking effort (--thinking)                │ ✅      │ ❌    │
│ Workspace file loading on startup           │ ✅      │ ❌    │
│ Virtual filesystem operations               │ ✅      │ ✅    │
│ File tools (read, write, ls, cd, rm, grep)  │ ✅      │ ✅    │
│ Research tools (search, summaries, fetch)   │ ✅      │ ✅    │
│ Multi-model support (openai, gemini, etc)   │ ✅      │ ⚠️    │
│ Provider-specific settings (reasoning, etc) │ ✅      │ ⚠️    │
│ Extended thinking output                    │ ✅      │ ❌    │
│ Session history                             │ ✅      │ ❌    │
└─────────────────────────────────────────────┴──────────┴────────┘

Legend: ✅ = Full parity  ⚠️ = Partial/Untested  ❌ = Missing
```

---

## Conclusion

The AI SDK port successfully replicates the core agent functionality in TypeScript. **The one-shot CLI mode is 70% feature-complete** and works for OpenAI. To achieve **full parity with the Python version**, we need:

1. **Add thinking effort control** (HIGH priority, 2h)
2. **Add workspace sync** (HIGH priority, 1.5h)
3. **Verify and implement provider settings** (MEDIUM, 1h)
4. **Implement extended thinking output** (MEDIUM, 1.5h)

These four improvements will bring the TypeScript port to feature parity with the Python equivalent for one-shot mode.
