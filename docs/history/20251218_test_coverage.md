# Testing Plan

Lightweight test coverage for pyagents - focus on core logic, skip framework responsibilities.

## Philosophy

Test what we own, mock what we don't:
- **Test:** VirtualFileSystem, file tools, command dispatch, path resolution
- **Skip:** TUI widgets (Textual's job), LLM responses (PydanticAI's job), external APIs

## Architecture

```
tests/
├── conftest.py          # Shared fixtures (vfs, deps, mock context)
├── test_virtual_fs.py   # VirtualFileSystem operations
├── test_tools.py        # Agent tool functions
└── test_commands.py     # Slash command dispatch
```

```
┌─────────────────────────────────────────────────────────────┐
│                      Test Boundaries                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   conftest  │───▶│  test_*.py   │───▶│  assertions   │  │
│  │  (fixtures) │    │  (units)     │    │  (outcomes)   │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         │                  │                               │
│         ▼                  ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Production Code                         │   │
│  │  VirtualFileSystem │ tools │ commands.dispatch      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼  (mocked)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              External Dependencies                   │   │
│  │  subprocess │ requests │ psycopg2 │ PydanticAI      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Test Coverage Map

### 1. VirtualFileSystem (`test_virtual_fs.py`)

| Method | Test Cases |
|--------|------------|
| `_resolve()` | absolute paths, relative paths, `.` and `..` normalization |
| `write()` | create file, overwrite file |
| `read()` | existing file, missing file error |
| `list_dir()` | empty dir, files only (no subdirs in listing) |
| `delete()` | existing file, missing file error |
| `load_from_disk()` | loads files with correct virtual paths |
| `save_to_disk()` | writes files to correct host paths |

### 2. Agent Tools (`test_tools.py`)

| Tool | Test Cases |
|------|------------|
| `write_file()` | delegates to vfs.write |
| `read_file()` | delegates to vfs.read |
| `run_shell()` | ls, pwd, cd, rm routing; unsupported command error |
| `run_shell(python)` | saves to disk, runs subprocess, returns output |

### 3. Command Dispatch (`test_commands.py`)

| Function | Test Cases |
|----------|------------|
| `@command` decorator | registers to REGISTRY |
| `dispatch()` | routes to handler, unknown command error, empty input |

## Fixtures (`conftest.py`)

```python
import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock
from pathlib import Path

from virtual_agent import VirtualFileSystem, AgentDeps

@pytest.fixture
def vfs():
    """Fresh VirtualFileSystem for each test."""
    return VirtualFileSystem()

@pytest.fixture
def deps(vfs, tmp_path):
    """AgentDeps with VFS and temp workspace."""
    return AgentDeps(fs=vfs, user_name="test", workspace_path=tmp_path)

@pytest.fixture
def mock_ctx(deps):
    """Mock RunContext with deps attached."""
    ctx = MagicMock()
    ctx.deps = deps
    return ctx
```

## Test Examples

### VirtualFileSystem

```python
# test_virtual_fs.py

def test_resolve_absolute_path(vfs):
    assert vfs._resolve("/foo/bar") == "/foo/bar"

def test_resolve_relative_path(vfs):
    vfs.cwd = "/home/user"
    assert vfs._resolve("docs/readme.md") == "/home/user/docs/readme.md"

def test_resolve_parent_directory(vfs):
    vfs.cwd = "/home/user/docs"
    assert vfs._resolve("../readme.md") == "/home/user/readme.md"

def test_write_and_read(vfs):
    vfs.write("test.txt", "hello")
    assert vfs.read("/home/user/test.txt") == "hello"

def test_read_missing_file(vfs):
    result = vfs.read("nonexistent.txt")
    assert "Error" in result

def test_list_dir_excludes_nested(vfs):
    vfs.files["/home/user/a.txt"] = "a"
    vfs.files["/home/user/sub/b.txt"] = "b"
    listing = vfs.list_dir("/home/user")
    assert "a.txt" in listing
    assert "b.txt" not in listing  # nested file excluded

def test_delete_file(vfs):
    vfs.write("temp.txt", "data")
    vfs.delete("temp.txt")
    assert "/home/user/temp.txt" not in vfs.files
```

### Agent Tools

```python
# test_tools.py
from virtual_agent import write_file, read_file, run_shell

def test_write_file_delegates(mock_ctx):
    result = write_file(mock_ctx, "test.py", "print('hi')")
    assert "Successfully wrote" in result
    assert mock_ctx.deps.fs.files["/home/user/test.py"] == "print('hi')"

def test_run_shell_ls(mock_ctx):
    mock_ctx.deps.fs.write("file.txt", "content")
    result = run_shell(mock_ctx, "ls")
    assert "file.txt" in result

def test_run_shell_cd(mock_ctx):
    run_shell(mock_ctx, "cd /tmp")
    assert mock_ctx.deps.fs.cwd == "/tmp"

def test_run_shell_unsupported(mock_ctx):
    result = run_shell(mock_ctx, "wget http://evil.com")
    assert "not implemented" in result
```

### Command Dispatch

```python
# test_commands.py
import pytest
from commands import REGISTRY, dispatch, command

@pytest.fixture
def mock_app():
    from unittest.mock import AsyncMock, MagicMock
    app = MagicMock()
    app.action_clear = AsyncMock()
    return app

@pytest.mark.asyncio
async def test_dispatch_unknown_command(mock_app):
    result = await dispatch(mock_app, "/foobar")
    assert "Unknown command" in result

@pytest.mark.asyncio
async def test_dispatch_empty_input(mock_app):
    result = await dispatch(mock_app, "/")
    assert "Type /help" in result

def test_command_decorator_registers():
    @command("testcmd", help="Test command")
    async def cmd_test(app, args):
        return "ok"

    assert "testcmd" in REGISTRY
    del REGISTRY["testcmd"]  # cleanup
```

## Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]
```

## Running Tests

```bash
# Install dev dependencies
uv sync --extra dev

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific file
uv run pytest tests/test_virtual_fs.py
```

## Implementation Phases

### Phase 1: Foundation
- [x] Add pytest dependencies to pyproject.toml
- [x] Create tests/ directory structure
- [x] Write conftest.py with fixtures

### Phase 2: Core Tests
- [x] Implement test_virtual_fs.py (path resolution, CRUD ops)
- [x] Implement test_tools.py (file tools, shell routing)
- [x] Verify all tests pass

### Phase 3: Command Tests
- [x] Implement test_commands.py (dispatch, registry)
- [x] Add pytest-asyncio for async command handlers

### Phase 4: Polish
- [x] Run full suite, fix any failures (37 passed)
- [x] Update STRUCTURE.md with test section
