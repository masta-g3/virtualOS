# Virtual OS

Minimal agent harness for testing LLM agentic capabilities with custom tools.

Built on [PydanticAI](https://ai.pydantic.dev/) - lightweight, no abstractions, easy to extend.

## Why

- Test how different models handle tool use, multi-step reasoning, and agentic workflows
- Add custom tools in minutes (one file, one list)
- Switch between OpenAI, Gemini, and Anthropic models with unified thinking control
- Sandboxed virtual filesystem - agent can't touch real files

## Quick Start

```bash
uv sync
cp .env.example .env  # Add API keys

# One-shot mode (scripting, quick queries)
uv run python virtual_agent.py "search for attention papers"

# Interactive TUI
uv run python tui.py
```

## Custom Tools

Add tools in `custom_tools.py`:

```python
def my_tool(ctx, query: str) -> str:
    """Tool description (shown to LLM)."""
    return f"Result: {query}"

TOOLS = [my_tool]
```

Tools are auto-loaded. The docstring becomes the tool description the LLM sees.

Access agent state via `ctx.deps`:
- `ctx.deps.fs` - VirtualFileSystem (read, write, list_dir)
- `ctx.deps.workspace_path` - Host workspace Path

See `llmpedia.py` for an example plugin connecting to an external PostgreSQL database.

## Modes

**CLI one-shot**: `uv run python virtual_agent.py "your prompt"` - streams output, exits when done.

**TUI interactive**: `uv run python tui.py` - minimal chat interface with session history, themes, keyboard shortcuts.

## TUI Commands

| Command | Action |
|---------|--------|
| `/model [name]` | Switch model (openai, gemini, haiku) |
| `/thinking [level]` | Set thinking effort (low, medium, high, off) |
| `/theme [name]` | Switch theme |
| `/files` | List virtual filesystem |
| `/sessions` | Browse session history |
| `/help` | Show all commands |

**Shortcuts**: `Ctrl+E` editor, `Ctrl+S` save workspace, `Ctrl+Y` copy mode, `Ctrl+L` clear.

## Models

| Key | Model | Thinking Control |
|-----|-------|------------------|
| `openai` | gpt-5.1-codex-mini | reasoning_effort |
| `gemini` | gemini-3-flash-preview | thinking_level |
| `haiku` | claude-haiku-4-5 | budget_tokens |

## Environment

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
```

## Documentation

See [docs/STRUCTURE.md](docs/STRUCTURE.md) for architecture details.
