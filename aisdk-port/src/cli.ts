import { runAgent } from "./agent.js";

async function main() {
  const prompt = process.argv.slice(2).join(" ");

  if (!prompt) {
    console.log("Usage: npx tsx src/cli.ts <prompt>");
    process.exit(1);
  }

  const result = await runAgent(prompt);
  console.log(result.text);
}

main().catch(console.error);
