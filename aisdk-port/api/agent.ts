import type { VercelRequest, VercelResponse } from "@vercel/node";
import { z } from "zod";
import { runAgent } from "../src/agent.js";
import { MODEL_KEYS, ModelKey, ThinkingEffort } from "../src/models.js";

const RequestSchema = z.object({
  prompt: z.string().min(1, "Prompt is required").max(10000),
  model: z.enum(MODEL_KEYS as [string, ...string[]]).optional(),
  thinkingEffort: z.enum(["low", "medium", "high"]).nullable().optional(),
});

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const parsed = RequestSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      error: "Validation failed",
      details: parsed.error.flatten(),
    });
  }

  const { prompt, model, thinkingEffort } = parsed.data;

  const result = await runAgent(prompt, {
    modelKey: model as ModelKey,
    thinkingEffort: thinkingEffort as ThinkingEffort,
  });

  return res.status(200).json(result);
}
