# agent-004: Add grep-like file content search to run_shell

**Status:** Done
**Completed:** 2025-12-19

## Summary

Added `grep` command to `run_shell` in both Python and TypeScript implementations, enabling the agent to search file contents in the virtual filesystem.

## Behavior

```
grep [-A NUM] [-B NUM] PATTERN [FILE_OR_DIR]
```

| Parameter | Description |
|-----------|-------------|
| `PATTERN` | Regex pattern |
| `FILE_OR_DIR` | Optional path (defaults to cwd) |
| `-A NUM` | Show NUM lines after each match |
| `-B NUM` | Show NUM lines before each match |

**Output format:**
- Match: `filepath:lineno:content`
- Context: `filepath:lineno-content`
- Non-adjacent groups separated by `--`
- Truncated at 100 lines

## Design Decisions

1. **Agent-controlled context lines** (like Claude Code) rather than AST-based (like Aider/Zed)
2. **Inline in run_shell** to match existing command pattern
3. **No case-insensitive flag** — agent can use `(?i)` regex inline
4. **No shlex parsing** — patterns with spaces require regex escaping (`hello\s+world`)

## Files Changed

- `virtual_agent.py` — grep command in run_shell
- `tests/test_tools.py` — 12 grep test cases
- `aisdk-port/src/virtual-fs.ts` — grep method with context support
- `aisdk-port/src/tools/file-tools.ts` — grep flag parsing
- `aisdk-port/tests/virtual-fs.test.ts` — 4 additional grep tests

## Test Results

- Python: 56 passed
- SDK: 55 passed
