import { config } from "dotenv";
import { runAgent, runAgentStreaming } from "./agent.js";
import { MODEL_KEYS, ModelKey, ThinkingEffort } from "./models.js";
import { VirtualFileSystem } from "./virtual-fs.js";

config({ quiet: true });

// Support both GOOGLE_API_KEY and GOOGLE_GENERATIVE_AI_API_KEY
process.env.GOOGLE_GENERATIVE_AI_API_KEY ??= process.env.GOOGLE_API_KEY;

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

  // Load workspace files (for local dev - no-op on Vercel)
  const fs = new VirtualFileSystem();
  fs.loadFromDisk("./workspace");

  const shouldStream = process.stdout.isTTY ?? false;

  if (shouldStream) {
    await runAgentStreaming(prompt, { modelKey, thinkingEffort, fs });
  } else {
    const result = await runAgent(prompt, { modelKey, thinkingEffort, fs });
    console.log(result.text);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}
