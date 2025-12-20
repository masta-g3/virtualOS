import { generateText, stepCountIs } from "ai";
import { VirtualFileSystem } from "./virtual-fs.js";
import { createFileTools } from "./tools/file-tools.js";
import { createResearchTools } from "./tools/research-tools.js";
import { createModel, ModelKey, ThinkingEffort } from "./models.js";

const SYSTEM_PROMPT = `\
You are a research assistant with access to the LLMpedia arXiv paper database.

## Tools

File operations:
- write_file(path, content): Create or overwrite a file
- read_file(path): Read file contents
- run_shell(command): Shell commands (ls, rm, pwd, cd, python)

Research tools:
- search_arxiv(...): Search papers by semantic query, title, author, date filters
- get_paper_summaries(codes, resolution): Get summaries at low/medium/high detail
- fetch_paper(code): Download full paper markdown to /home/user/papers/

## Research Workflow

### Two Modes

**Narrow/Deep** (1-3 papers, need details):
- Skip summaries, fetch full papers directly
- Example: "Find the original attention paper" → download and read

**Broad/Survey** (5+ papers, need overview):
- Start with low/medium summaries, triage, then escalate selectively
- Example: "RLHF advances?" → summaries first → drill into 2-3

### Escalation Path
low summary → medium → high → full paper

### Flow
1. DISCOVER: search_arxiv with appropriate filters
2. EVALUATE: Choose narrow/deep or broad/survey path
3. ESCALATE: Only fetch full papers when summaries aren't enough
4. ITERATE: Refine queries, follow interesting threads
5. SYNTHESIZE: Review scratchpad, cite papers with arxiv codes

## Scratchpad

Maintain /home/user/scratchpad.md to accumulate findings:
- read_file to get current state
- Append new findings
- write_file to save updates
`;

export interface AgentOptions {
  modelKey?: ModelKey;
  thinkingEffort?: ThinkingEffort;
  fs?: VirtualFileSystem;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result: string;
}

export interface AgentResult {
  text: string;
  steps: number;
  files: Record<string, string>;
  toolCalls: ToolCall[];
  reasoning?: string;
}

export async function runAgent(
  prompt: string,
  options: AgentOptions = {}
): Promise<AgentResult> {
  const { modelKey = "openai", thinkingEffort = "high", fs: providedFs } = options;
  const { model, providerOptions, maxTokens } = createModel(modelKey, thinkingEffort);

  const fs = providedFs ?? new VirtualFileSystem();
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

  const toolCalls: ToolCall[] = [];
  for (const step of result.steps) {
    if (step.toolCalls) {
      for (const tc of step.toolCalls) {
        const toolResult = step.toolResults?.find(
          (r) => r.toolCallId === tc.toolCallId
        );
        toolCalls.push({
          name: tc.toolName,
          args: tc.input as Record<string, unknown>,
          result: String(toolResult?.output ?? ""),
        });
      }
    }
  }

  // Extract reasoning from steps (for extended thinking models)
  let reasoning: string | undefined;
  for (const step of result.steps) {
    if (step.reasoning) {
      reasoning = (reasoning ? reasoning + "\n\n" : "") + step.reasoning.map(r => r.text).join("\n");
    }
  }

  return {
    text: result.text,
    steps: result.steps.length,
    files: Object.fromEntries(fs.files),
    toolCalls,
    reasoning,
  };
}
