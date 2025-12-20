import { describe, it, expect } from "vitest";
import { parseArgs } from "../src/cli.js";

describe("parseArgs", () => {
  it("defaults to openai model and high thinking", () => {
    const result = parseArgs(["search for papers"]);
    expect(result.modelKey).toBe("openai");
    expect(result.thinkingEffort).toBe("high");
    expect(result.prompt).toBe("search for papers");
  });

  it("extracts model from -m flag", () => {
    const result = parseArgs(["-m", "gemini", "find", "papers"]);
    expect(result.modelKey).toBe("gemini");
    expect(result.prompt).toBe("find papers");
  });

  it("ignores invalid model key", () => {
    const result = parseArgs(["-m", "invalid", "test"]);
    expect(result.modelKey).toBe("openai");
  });

  it("extracts thinking effort from -t flag", () => {
    const result = parseArgs(["-t", "low", "test"]);
    expect(result.thinkingEffort).toBe("low");
  });

  it("handles --thinking flag", () => {
    const result = parseArgs(["--thinking", "medium", "query"]);
    expect(result.thinkingEffort).toBe("medium");
  });

  it("handles thinking off", () => {
    const result = parseArgs(["-t", "off", "test"]);
    expect(result.thinkingEffort).toBe(null);
  });

  it("combines model and thinking flags", () => {
    const result = parseArgs(["-m", "anthropic", "-t", "high", "question"]);
    expect(result.modelKey).toBe("anthropic");
    expect(result.thinkingEffort).toBe("high");
    expect(result.prompt).toBe("question");
  });
});
