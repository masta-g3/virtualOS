# Project Structure

PydanticAI agent experiments - sandboxed AI agents with tool use.

## Philosophy

**Less is more.** This codebase prioritizes simplicity and clarity over features. Before adding anything, ask: is this essential?

- `virtual_agent.py` is ~200 lines - one agent, file tools + research tools
- `tui.py` is ~280 lines - view layer with visual polish (tree-style messages, animated status)
- No abstractions until proven necessary
- No configuration beyond what's needed
- No defensive code in trusted paths

## Architecture

```
pydantic-agents/
├── virtual_agent.py    # Agent library (VirtualFileSystem, create_agent, MODELS)
├── tui.py              # Textual TUI (imports from virtual_agent)
├── commands.py         # Slash command registry and handlers
├── theme.py            # Theme loader (load, list, generate CSS)
├── settings.py         # User settings persistence
├── themes/             # Built-in themes (YAML)
│   ├── amber-dark.yaml
│   ├── catppuccin-macchiato.yaml
│   ├── gruvbox-dark.yaml
│   └── solarized-light.yaml
├── research_tools.py   # LLMpedia DB queries (search, summaries, download)
├── workspace/          # Synced with VirtualFileSystem (ctrl+s to save)
│   └── papers/         # Downloaded arXiv paper markdowns
├── tests/              # pytest test suite
│   ├── conftest.py        # Shared fixtures
│   ├── test_virtual_fs.py # VirtualFileSystem tests
│   ├── test_tools.py      # Agent tool tests
│   └── test_commands.py   # Slash command tests
├── pyproject.toml      # Dependencies (uv)
├── .env                # API keys (not committed)
└── docs/
    ├── STRUCTURE.md       # This file
    ├── TESTING.md         # Test suite documentation
    ├── VISUAL_IDENTITY.md # TUI design system (colors, prefixes, motion)
    └── history/           # Archived feature specs
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
        ┌──────────┬───────────┼───────────┬──────────────┐
        ▼          ▼           ▼           ▼              ▼
┌────────────┐ ┌────────┐ ┌──────────┐ ┌────────────┐ ┌───────────┐
│ write_file │ │read_file│ │run_shell │ │search_arxiv│ │fetch_paper│
└─────┬──────┘ └───┬────┘ └────┬─────┘ └─────┬──────┘ └─────┬─────┘
      │            │           │             │              │
      └────────────┼───────────┘             │              │
                   ▼                         ▼              ▼
┌─────────────────────────────────┐  ┌─────────────────────────────┐
│      VirtualFileSystem          │  │      research_tools.py      │
│  (in-memory dict, sandboxed)    │  │  (LLMpedia DB + S3)         │
└─────────────────────────────────┘  └─────────────────────────────┘
```

**File Tools:**

| Tool | Purpose | Parameters |
|------|---------|------------|
| `write_file` | Create/overwrite files | `path`, `content` |
| `read_file` | Read file contents | `path` |
| `run_shell` | Shell commands | `command` (ls, rm, pwd, cd, python) |

**Research Tools:**

| Tool | Purpose | Parameters |
|------|---------|------------|
| `search_arxiv` | Search papers in LLMpedia | `query`, `title_contains`, `author`, `published_after/before`, `limit` |
| `get_paper_summaries` | Get summaries at resolution | `arxiv_codes`, `resolution` (low/medium/high) |
| `fetch_paper` | Download full paper to VFS | `arxiv_code` |

**Key components:**

- `VirtualFileSystem` - Dataclass holding `files: dict[str, str]` and `cwd: str`
- `AgentDeps` - Dependency injection container passed to tools via `RunContext`
- Structured tools for file ops (no shell parsing issues)

**Safety:** All file operations happen in a Python dictionary. The agent cannot access the real filesystem.

### Research Workflow

The agent supports two research modes against the LLMpedia arXiv database:

**Narrow/Deep** (1-3 papers): Skip summaries → `fetch_paper` → `read_file`

**Broad/Survey** (5+ papers): `search_arxiv` → `get_paper_summaries` (low/medium) → triage → escalate selectively

Escalation path: low summary → medium → high → full paper

The agent maintains a scratchpad at `/home/user/scratchpad.md` to accumulate research findings.

## Adding New Agents

1. Create a new Python file (e.g., `my_agent.py`)
2. Define dependencies dataclass for state
3. Create `Agent()` with model, deps_type, and system_prompt
4. Add tools with `@agent.tool` decorator
5. Run with `asyncio.run()`

Example pattern:
```python
from pydantic_ai import Agent, RunContext

@dataclass
class MyDeps:
    state: MyState

agent = Agent("openai:gpt-4.1-mini", deps_type=MyDeps)

@agent.tool
def my_tool(ctx: RunContext[MyDeps], arg: str) -> str:
    return ctx.deps.state.do_something(arg)
```

## Running

```bash
# CLI mode
uv run python virtual_agent.py

# TUI mode (interactive terminal interface)
uv run python tui.py
```

## Workspace Sync

The TUI loads files from `./workspace/` into the virtual filesystem on startup:
- Files appear at `/home/user/*` in the VFS
- Agent can read/modify these files
- Press `ctrl+s` to save changes back to `./workspace/`
- Header shows `[modified]` when unsaved changes exist

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
- Anthropic: `budget_tokens` (1024/4096/16384)

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
- `psycopg2-binary` - PostgreSQL client (research_tools)
- `google-genai` - Gemini embeddings for semantic search
- `requests` - HTTP client for S3 downloads

Dev dependencies (`uv sync --extra dev`):
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
