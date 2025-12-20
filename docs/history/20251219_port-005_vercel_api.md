# port-005: Vercel API Route for Agent

**Status:** Done
**Priority:** 2

## Summary

Exposed the AI SDK agent via Vercel serverless API route for HTTP-based invocation.

## Implementation

### API Endpoint: `POST /api/agent`

**Request:**
```json
{
  "prompt": "string (required, 1-10000 chars)",
  "model": "openai | gemini | anthropic (optional)",
  "thinkingEffort": "low | medium | high | null (optional)"
}
```

**Response:**
```json
{
  "text": "Agent response text",
  "steps": 2,
  "files": {},
  "toolCalls": [
    {"name": "runShell", "args": {"command": "ls"}, "result": "(empty directory)"}
  ],
  "reasoning": "Extended thinking output (if enabled)"
}
```

**Error Responses:**
- `400`: Validation failed (invalid prompt, unknown model)
- `405`: Method not allowed (non-POST)
- `500`: Agent execution error

### Files

| File | Description |
|------|-------------|
| `api/agent.ts` | Vercel serverless POST handler with Zod validation |
| `vercel.json` | Function config (60s timeout, 1GB memory) |
| `src/agent.ts` | Added ToolCall interface, tool call extraction, reasoning capture |

### Testing

```bash
# Start dev server
npm run serve

# Test basic request
curl -X POST http://localhost:3000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"prompt": "List files"}'

# Test with options
curl -X POST http://localhost:3000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Search papers", "model": "anthropic", "thinkingEffort": "high"}'
```

## Architecture

```
HTTP POST /api/agent
       │
       ▼
┌─────────────────┐
│  api/agent.ts   │  Zod validation → runAgent() → JSON response
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  src/agent.ts   │  generateText() with tools → AgentResult
└─────────────────┘
```

## Notes

- Environment variables (API keys) configured in Vercel dashboard
- Local dev uses `.env` file
- Tool calls visible in response for debugging/UI
- Reasoning output included when extended thinking enabled
