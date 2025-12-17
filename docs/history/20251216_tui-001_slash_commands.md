# tui-001: Slash Commands System

Extensible command system for the TUI—invoke actions with `/command` syntax.

## Summary

- [x] Decorator-based command registry (`@command` decorator)
- [x] `/help` — list available commands
- [x] `/clear` — save conversation and start fresh
- [x] `/sync` — save workspace files to disk
- [x] `/model [NAME]` — show or change LLM model
- [x] `/files` — list virtual filesystem contents
- [x] `/quit` — exit the application

## Architecture

```
User input "/model gpt-4o"
       │
       ▼
┌──────────────────┐
│ on_input_submit  │  tui.py detects "/" prefix
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ commands.dispatch│  Parse command + args, lookup registry
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ handler(app,args)│  Execute and return output
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Display result   │  Markdown with .agent-message styling
└──────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `commands.py` | Registry, `@command` decorator, `dispatch()`, built-in commands |
| `tui.py` | Routes `/` prefixed input to dispatcher |

## Design Decisions

- **Decorator registration** over class hierarchy — minimal, self-documenting
- **`.agent-message` styling** for command output — markdown-compatible, visually consistent
- **Case-insensitive** command names
- **Keybindings preserved** — ctrl+s/l/c still work alongside slash commands
