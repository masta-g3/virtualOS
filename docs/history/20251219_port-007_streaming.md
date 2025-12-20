# port-007: Streaming Mode for CLI One-Shot

Streaming output for both Python and TypeScript CLI one-shot modes with real-time text, tool call visibility, and reasoning display.

## Summary

- [x] Python: `run_streaming()` using `agent.run_stream_events()`
- [x] TypeScript: `runAgentStreaming()` using `streamText()` with `fullStream`
- [x] TTY auto-detection for streaming vs plain output
- [x] Tool calls shown with `[tool]` and `[result]` prefixes
- [x] Reasoning/thinking tokens displayed in gray
- [x] Works with OpenAI, Gemini, and Anthropic providers

## Key Implementation Details

**Python:** Uses PydanticAI's `run_stream_events()` to iterate over `FunctionToolCallEvent`, `FunctionToolResultEvent`, and `PartDeltaEvent` (with `ThinkingPartDelta`).

**TypeScript:** Uses AI SDK's `streamText()` with `fullStream` property. Key finding: use `stopWhen: stepCountIs(N)` instead of `maxSteps` for multi-step tool calls - `maxSteps` doesn't work correctly with `streamText`.

**TTY Detection:**
- Python: `sys.stdout.isatty()`
- TypeScript: `process.stdout.isTTY`

## Output Format

```
[tool] search_arxiv(query="attention", limit=3)
[result] Found 3 papers: 2304.04556...

Based on my research, attention mechanisms...

[3 steps, 2 tool calls]
```

## Sources

- [AI SDK streamText multi-step issue](https://github.com/vercel/ai/discussions/3327)
- [PydanticAI Streaming](https://ai.pydantic.dev/agents/#streaming)
