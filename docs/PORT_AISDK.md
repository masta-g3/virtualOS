# AI SDK Port - Project Overview

Lightweight TypeScript port of the PydanticAI research agent to Vercel AI SDK.

## Goal

1:1 behavioral parity with `virtual_agent.py` — same tools, same system prompt, same research workflow. No TUI, only one-shot mode for Vercel webapp integration.

## Architecture Mapping

```
Python (PydanticAI)              →  TypeScript (AI SDK)
─────────────────────────────────────────────────────────
pydantic_ai.Agent                →  generateText() + tools
@agent.tool                      →  tool() from 'ai'
RunContext[AgentDeps]            →  closure over deps
agent.run(prompt, deps=deps)     →  generateText({ prompt, tools })
UsageLimits                      →  stopWhen: stepCountIs(N)
```

## Directory Structure

```
aisdk-port/
├── src/
│   ├── agent.ts           # createAgent(), generateText config
│   ├── virtual-fs.ts      # VirtualFileSystem class
│   ├── tools/
│   │   ├── file-tools.ts  # write_file, read_file, run_shell
│   │   └── research-tools.ts  # search_arxiv, get_paper_summaries, fetch_paper
│   ├── models.ts          # Multi-model registry + thinking effort mapping
│   └── types.ts           # Shared interfaces (Prisma function signatures)
├── cli.ts                 # One-shot CLI mode
├── route.ts               # Vercel API route handler (example)
├── package.json
└── tsconfig.json
```

## Core Components

### 1. VirtualFileSystem

Exact port of Python dataclass:

```typescript
class VirtualFileSystem {
  files: Map<string, string> = new Map();
  cwd: string = '/home/user';

  resolve(path: string): string { /* normalize . and .. */ }
  write(path: string, content: string): string;
  read(path: string): string;
  listDir(path: string): string;
  delete(path: string): string;
}
```

### 2. Tool Definitions (AI SDK format)

```typescript
import { tool } from 'ai';
import { z } from 'zod';

const writeFile = tool({
  description: 'Write content to a file (creates or overwrites).',
  inputSchema: z.object({
    path: z.string().describe('File path (relative to cwd or absolute)'),
    content: z.string().describe('Complete file content'),
  }),
  execute: async ({ path, content }) => fs.write(path, content),
});
```

### 3. Multi-Model Support

**Important**: Use `openai.responses()` (Responses API) for OpenAI, not regular `openai()`.

| Model Key | AI SDK Pattern | Model ID |
|-----------|----------------|----------|
| `openai`  | `openai.responses('...')` | `gpt-5.1-codex-mini` |
| `gemini`  | `google('...')` | `gemini-3-flash-preview` |
| `haiku`   | `anthropic('...')` | `claude-haiku-4-5` |

```typescript
// OpenAI - use Responses API for agentic workflows
import { openai } from '@ai-sdk/openai';
const model = openai.responses('gpt-5.1-codex-mini');

// Gemini
import { google } from '@ai-sdk/google';
const model = google('gemini-3-flash-preview');

// Anthropic
import { anthropic } from '@ai-sdk/anthropic';
const model = anthropic('claude-haiku-4-5');
```

Thinking effort maps to provider-specific options:
- **OpenAI**: `reasoningEffort` in providerOptions (low/medium/high)
- **Gemini**: `thinkingConfig.thinkingLevel` (low/high)
- **Anthropic**: `thinking.budgetTokens` (1024/4096/16384)

### 4. Research Tools (Prisma Integration)

Unlike Python's direct psycopg2 connection, the JS port uses **injected Prisma functions**:

```typescript
interface ResearchDeps {
  searchPapers: (params: SearchParams) => Promise<Paper[]>;
  getSummaries: (codes: string[], resolution: string) => Promise<Record<string, string>>;
  getEmbedding: (text: string) => Promise<number[]>;
}

// Injected at agent creation, not hardcoded
const agent = createAgent({ researchDeps: prismaResearchDeps });
```

This allows the Vercel webapp to provide its own Prisma client while keeping the agent code portable.

## API Usage

### One-Shot CLI

```bash
bun run cli.ts "search for attention papers"
```

### Vercel API Route

```typescript
// app/api/agent/route.ts
import { createAgent } from '@/lib/agent';

export async function POST(req: Request) {
  const { prompt } = await req.json();
  const result = await createAgent().run(prompt);
  return Response.json({ text: result.text, steps: result.steps });
}
```

## Key Differences from Python

| Aspect | Python | TypeScript |
|--------|--------|------------|
| DB Connection | Direct psycopg2 | Injected Prisma functions |
| Embeddings | google-genai client | @google/generative-ai or passed in |
| Tool Context | RunContext[AgentDeps] | Closure over deps object |
| Async Model | asyncio | Native async/await |
| Tool Loop | UsageLimits | stopWhen: stepCountIs(N) |

## Feature Tracking

Epic: `port`

| ID | Description | Priority | Status |
|----|-------------|----------|--------|
| port-001 | Basic generateText agent | 1 | pending |
| port-002 | VirtualFileSystem + file tools | 1 | pending |
| port-003 | Research tools (Prisma) | 2 | pending |
| port-004 | Multi-model configuration | 2 | pending |
| port-005 | Vercel API route | 2 | pending |
| port-006 | CLI one-shot mode | 3 | pending |

Use `/next-feature` to start implementation.
