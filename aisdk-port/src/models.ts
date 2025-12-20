import { openai } from "@ai-sdk/openai";
import { google } from "@ai-sdk/google";
import { anthropic } from "@ai-sdk/anthropic";

export type ModelKey = "openai" | "gemini" | "anthropic";
export type ThinkingEffort = "low" | "medium" | "high" | null;

export interface ModelConfig {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  model: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  providerOptions?: Record<string, any>;
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
      // gpt-5.1-codex-mini is a reasoning model - supports reasoningEffort
      return {
        model: openai("gpt-5.1-codex-mini"),
        providerOptions: thinkingEffort
          ? { openai: { reasoningEffort: thinkingEffort } }
          : undefined,
      };

    case "gemini":
      return {
        model: google("gemini-3-flash-preview"),
      };

    case "anthropic": {
      // claude-haiku-4-5 supports extended thinking
      if (thinkingEffort) {
        const budget = THINKING_BUDGETS[thinkingEffort];
        return {
          model: anthropic("claude-haiku-4-5"),
          maxTokens: budget + 8192,
          providerOptions: {
            anthropic: { thinking: { type: "enabled", budgetTokens: budget } },
          },
        };
      }
      return { model: anthropic("claude-haiku-4-5") };
    }
  }
}

export const MODEL_KEYS: ModelKey[] = ["openai", "gemini", "anthropic"];
