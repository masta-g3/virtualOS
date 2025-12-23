# Virtual OS

Minimal agent harness for testing LLM agentic capabilities with custom tools.

## Philosophy

**Less is more.** This codebase prioritizes simplicity and clarity over features. Before adding anything, ask: is this essential?

- `virtual_agent.py` is ~200 lines - one agent, file tools + research tools
- `tui.py` is ~280 lines - view layer with visual polish (tree-style messages, animated status)
- No abstractions until proven necessary
- No configuration beyond what's needed
- No defensive code in trusted paths

## Architecture

```
pyagents/
├── virtual_agent.py    # Agent core (VirtualFileSystem, create_agent, built-in tools)
├── custom_tools.py     # User-defined tools (auto-loaded)
├── llmpedia.py         # Example plugin: arXiv paper search (auto-loaded)
├── tui.py              # Textual TUI for interactive chat
├── commands.py         # Slash command registry
├── theme.py            # Theme loader
├── settings.py         # User settings persistence
├── themes/             # Built-in themes (YAML)
├── workspace/          # Synced with VirtualFileSystem (ctrl+s to save)
├── tests/              # pytest test suite
├── pyproject.toml      # Dependencies (uv)
├── .env                # API keys (not committed)
└── docs/
    └── STRUCTURE.md    # Architecture details
```

## Core Concepts

### Virtual Filesystem Agent (`virtual_agent.py`)

A PydanticAI agent operating in a sandboxed environment:

```
┌─────────────────────────────────────────────────────────────────┐
│                            Agent                                │
│           (LLM with system prompt + tool access)                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ calls
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Core Tools      │  │  llmpedia.py      │  │  custom_tools.py  │
│ write/read/shell  │  │  (example plugin) │  │  (user tools)     │
└─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│ VirtualFileSystem │  │ PostgreSQL + S3   │  │ Your backends...  │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

**Core Tools** (built-in):

| Tool | Purpose |
|------|---------|
| `write_file` | Create/overwrite files in VFS |
| `read_file` | Read file contents from VFS |
| `run_shell` | Shell commands (ls, rm, pwd, cd, mkdir, touch, mv, grep, python) |

**Key components:**

- `VirtualFileSystem` - In-memory dict, sandboxed (agent can't touch real files)
- `AgentDeps` - Dependency container passed to tools via `ctx.deps`

## LLMpedia Plugin (`llmpedia.py`)

Example of connecting to an external database/knowledge base. Shows the pattern for building plugins.

| Tool | Purpose |
|------|---------|
| `search_arxiv` | Semantic + filter search against LLMpedia PostgreSQL |
| `get_paper_summaries` | Multi-resolution summaries (low/medium/high) |
| `fetch_paper` | Download full paper markdown from S3 to VFS |

To disable: delete or rename `llmpedia.py` (tools auto-load via try/except).

## Custom Tools

Add tools in `custom_tools.py`:

```python
def my_tool(ctx, query: str) -> str:
    """Tool description (shown to LLM)."""
    return f"Result: {query}"

TOOLS = [my_tool]
```

Access agent state via `ctx.deps`:
- `ctx.deps.fs` - VirtualFileSystem instance (read, write, list_dir, delete)
- `ctx.deps.workspace_path` - Host workspace Path

Tools are automatically loaded on agent startup. The docstring becomes the tool description the LLM sees.

## Running

```bash
# CLI one-shot (scripting, quick queries)
uv run python virtual_agent.py "search for attention papers"

# TUI mode (interactive terminal interface)
uv run python tui.py
```

## Workspace Sync

The TUI loads files from `./workspace/` into the virtual filesystem on startup:
- Files appear at `/home/user/*` in the VFS
- Agent can read/modify these files
- Press `ctrl+s` to save changes back to `./workspace/`
- Header shows `[modified]` when unsaved changes exist

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message (single-line mode) |
| Ctrl+C | Quit |
| Ctrl+E | Open $EDITOR for multi-line input |
| Ctrl+J | Send message (multi-line mode) |
| Ctrl+L | Clear (new session) |
| Ctrl+S | Save workspace |
| Ctrl+Y | Copy mode (select block to copy) |
| ↑/↓ | Navigate input history |
| Esc | Rewind mode (edit previous message) |

## Model Configuration

The agent supports multiple LLM providers with unified thinking effort control:

| Model Key | Provider | Model ID |
|-----------|----------|----------|
| `openai` | OpenAI | `gpt-5.1-codex-mini` (reasoning) |
| `gemini` | Google | `gemini-3-flash-preview` |
| `haiku` | Anthropic | `claude-haiku-4-5` |

**Slash commands:**
- `/model` - Open model selector (↑↓ to navigate, Enter to select, ESC to cancel)
- `/model <name>` - Switch to model directly
- `/thinking` - Open thinking level selector
- `/thinking <level>` - Set level directly (low, medium, high, off)
- `/theme` - Open theme selector
- `/theme <name>` - Switch theme directly
- `/theme list` - List available themes

**Thinking effort** maps to each provider's native config:
- OpenAI: `reasoning_effort` parameter
- Gemini: `thinking_level` in thinking config
- Anthropic: `budget_tokens` (1024/4096/16384), `max_tokens` = budget + 8192

## Testing

```bash
# Install dev dependencies
uv sync --extra dev

# Run all tests
uv run pytest

# Run specific file
uv run pytest tests/test_virtual_fs.py -v
```

See `docs/history/20251218_test_coverage.md` for test design details.

## Dependencies

Managed via `uv`. Key packages:
- `pydantic-ai` - Agent framework
- `textual` - TUI framework
- `pyyaml` - Theme file parsing
- `python-dotenv` - Load `.env` files
- `psycopg2-binary` - PostgreSQL client (llmpedia plugin)
- `google-genai` - Gemini embeddings (llmpedia semantic search)
- `requests` - HTTP client (llmpedia S3 downloads)

Dev dependencies (`uv sync --extra dev`):
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
