# cli-001: CLI One-Shot Mode

One-shot CLI interface for `virtual_agent.py` — scripting and quick queries without TUI.

## Usage

```bash
uv run python virtual_agent.py "search for attention papers"
uv run python virtual_agent.py "list files"
```

For interactive mode, use `python tui.py`.

## Design Rationale

**One-shot only, no REPL.** A basic `input()` REPL would lack thinking indicators, tool visibility, and proper async handling. The TUI already handles interactive use well.

## Summary

- [x] Replaced hardcoded demo `main()` with CLI argument parsing
- [x] Loads workspace files (same as TUI)
- [x] Prints agent response and exits
