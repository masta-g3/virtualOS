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
├── virtual_agent.py    # Agent library (VirtualFileSystem, AgentDeps, agent)
├── tui.py              # Textual TUI (imports from virtual_agent)
├── tui.tcss            # TUI styles
├── commands.py         # Slash command registry and handlers
├── research_tools.py   # LLMpedia DB queries (search, summaries, download)
├── workspace/          # Synced with VirtualFileSystem (ctrl+s to save)
│   └── papers/         # Downloaded arXiv paper markdowns
├── pyproject.toml      # Dependencies (uv)
├── .env                # API keys (not committed)
└── docs/
    ├── STRUCTURE.md       # This file
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

## Dependencies

Managed via `uv`. Key packages:
- `pydantic-ai` - Agent framework
- `textual` - TUI framework
- `python-dotenv` - Load `.env` files
- `psycopg2-binary` - PostgreSQL client (research_tools)
- `google-genai` - Gemini embeddings for semantic search
- `requests` - HTTP client for S3 downloads
