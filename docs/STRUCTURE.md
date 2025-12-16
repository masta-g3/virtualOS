# Project Structure

PydanticAI agent experiments - sandboxed AI agents with tool use.

## Philosophy

**Less is more.** This codebase prioritizes simplicity and clarity over features. Before adding anything, ask: is this essential?

- `virtual_agent.py` is ~100 lines - one agent, one tool, one dataclass
- `tui.py` is ~100 lines - thin view layer, imports agent, no duplication
- No abstractions until proven necessary
- No configuration beyond what's needed
- No defensive code in trusted paths

## Architecture

```
pydantic-agents/
├── virtual_agent.py    # Agent library (VirtualFileSystem, AgentDeps, agent)
├── tui.py              # Textual TUI (imports from virtual_agent)
├── tui.tcss            # TUI styles
├── workspace/          # Synced with VirtualFileSystem (ctrl+s to save)
├── pyproject.toml      # Dependencies (uv)
├── .env                # API keys (not committed)
└── docs/
    ├── STRUCTURE.md    # This file
    └── history/        # Archived feature specs
```

## Core Concepts

### Virtual Filesystem Agent (`virtual_agent.py`)

A PydanticAI agent operating in a sandboxed environment:

```
┌─────────────────────────────────────────────┐
│                   Agent                     │
│  (LLM with system prompt + tool access)     │
└─────────────────┬───────────────────────────┘
                  │ calls
                  ▼
┌─────────────────────────────────────────────┐
│              run_shell tool                 │
│  (ls, cat, echo, rm, pwd, cd)               │
└─────────────────┬───────────────────────────┘
                  │ manipulates
                  ▼
┌─────────────────────────────────────────────┐
│          VirtualFileSystem                  │
│  (in-memory dict, no real disk access)      │
└─────────────────────────────────────────────┘
```

**Key components:**

- `VirtualFileSystem` - Dataclass holding `files: dict[str, str]` and `cwd: str`
- `AgentDeps` - Dependency injection container passed to tools via `RunContext`
- `run_shell` - Tool decorated with `@agent.tool`, parses shell-like commands

**Safety:** All file operations happen in a Python dictionary. The agent cannot access the real filesystem.

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
