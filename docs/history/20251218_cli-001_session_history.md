# CLI-001: Session History View

Add a minimal session history feature to the TUI that allows users to browse, resume, and delete previous conversations. New app launches start with a fresh conversation.

## Solution

Reuse the existing `SelectorScreen` modal pattern to show a session list, accessible via `/sessions` command. Sessions are identified by their first user message (truncated to 40 chars).

```
┌─────────────────────────────────────────┐
│  Sessions                               │
├─────────────────────────────────────────┤
│    "Help me write a Python script..."   │
│    "What is the capital of France?"     │
│  → "Search arxiv for transformer..."    │  ← current session
└─────────────────────────────────────────┘
```

- **Enter** - Resume highlighted session
- **d** - Delete highlighted session (power user, documented in `/help`)
- **Esc** - Cancel

## Architecture

```
VirtualAgentApp
├─ conversations: dict[str, ConversationData]
├─ conversation_id: str (current)
├─ history: list[ModelMessage]
│
├─ show_sessions_selector()
├─ _on_session_action(result)
├─ _load_conversation(id)
└─ _delete_conversation(id)

SessionSelectorScreen
├─ extends ModalScreen
├─ delete binding (d key)
└─ returns tuple: (action, session_id)
```

## Summary

- [x] Fresh start on launch (always new session)
- [x] `/sessions` command opens modal
- [x] Resume: persists current, loads selected, re-renders UI
- [x] Delete: removes from dict, persists, reopens selector
- [x] Edge cases: no sessions, delete current (prevented), empty session preview

## Files Changed

| File | Changes |
|------|---------|
| `tui.py` | +47 lines: `get_session_preview()`, `SessionSelectorScreen`, app methods |
| `commands.py` | +5 lines: `/sessions` command |
