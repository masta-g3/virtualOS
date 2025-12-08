# Project Structure

PydanticAI agent experiments - sandboxed AI agents with tool use.

## Architecture

```
pydantic-agents/
├── virtual_agent.py    # Main agent script
├── pyproject.toml      # Dependencies (uv)
├── .env                # API keys (not committed)
└── docs/
    └── STRUCTURE.md    # This file
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
uv run python virtual_agent.py
```

## Dependencies

Managed via `uv`. Key packages:
- `pydantic-ai` - Agent framework
- `python-dotenv` - Load `.env` files
