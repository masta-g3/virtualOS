# agent-008: Structured File Tools

Replaced fragile shell-style `echo` parsing with dedicated PydanticAI tools for file operations.

## Problem

Shell parsing for file writes had fundamental escaping issues:
- `\n` inside strings converted to newlines (broke Python string literals)
- `>` in content broke filename parsing
- Nested quotes impossible to handle reliably

## Solution

Added structured tools that use JSON serialization (escaping handled automatically):

| Tool | Purpose | Parameters |
|------|---------|------------|
| `write_file` | Create/overwrite files | `path`, `content` |
| `read_file` | Read file contents | `path` |
| `run_shell` | Shell commands only | `command` (ls, rm, pwd, cd, python) |

## Research Sources

- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) - "Avoid string-escaping complications"
- [Claude Code tools](https://gist.github.com/bgauryy/0cdb9aa337d01ae5bd0c803943aa36bd) - Separate Read/Write/Edit tools
- [Aider edit formats](https://aider.chat/docs/more/edit-formats.html) - "Avoid line numbers, clearly delimit code"
- [LangChain FileManagementToolkit](https://python.langchain.com/v0.1/docs/integrations/tools/filesystem/) - WriteFileTool pattern

## Implementation Summary

- [x] Add `write_file` tool to `virtual_agent.py`
- [x] Add `read_file` tool to `virtual_agent.py`
- [x] Update system prompt to document tools
- [x] Remove `echo >` file redirection from run_shell
- [x] Remove `cat` command (replaced by read_file)
- [x] Update `docs/STRUCTURE.md` with new architecture

## Future: edit_file (if needed)

```python
@agent.tool
def edit_file(ctx: RunContext[AgentDeps], path: str, old: str, new: str) -> str:
    """Replace exact match of old with new in file."""
    content = ctx.deps.fs.read(path)
    if old not in content:
        return f"Error: text not found in {path}"
    return ctx.deps.fs.write(path, content.replace(old, new, 1))
```

YAGNI for now — whole-file rewrites via `write_file` sufficient for small scripts.
