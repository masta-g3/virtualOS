# model-001: Multi-Model Support

Configurable model selection with unified thinking effort parameter.

## Models

| Key | Provider | Model ID |
|-----|----------|----------|
| `openai` | OpenAI | `gpt-5.1-codex-mini` (reasoning) |
| `gemini` | Google | `gemini-3-flash-preview` |
| `haiku` | Anthropic | `claude-haiku-4-5` |

## Thinking Effort

Unified `thinking_effort` parameter maps to provider-specific settings:

| Provider | Parameter | Mapping |
|----------|-----------|---------|
| OpenAI | `reasoning_effort` | Direct pass-through |
| Gemini | `thinking_level` | Direct pass-through |
| Anthropic | `budget_tokens` | low→1024, medium→4096, high→16384 |

`None` behavior: OpenAI → `"none"`, Gemini → `"minimal"`, Anthropic → disabled (opt-in).

## TUI Commands

- `/model` - Open model selector (↑↓, Enter, ESC)
- `/model <name>` - Direct switch
- `/thinking` - Open thinking selector
- `/thinking <level>` - Direct set (low, medium, high, off)

## Implementation

- `TOOLS` list with explicit tool functions
- `create_agent(model_key, thinking_effort)` factory
- `SelectorScreen` modal for interactive selection
