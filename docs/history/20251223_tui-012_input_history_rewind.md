# tui-012: Input History & Conversation Rewind

## Summary

Two complementary message handling features:

1. **Input History** (↑/↓): Navigate previous user inputs in the prompt box
2. **Conversation Rewind** (Esc): Roll back conversation state to edit and resend

## Features

### Input History
- ↑/↓ arrows cycle through previously sent prompts
- Draft preservation: current input saved when navigating, restored on ↓ past newest
- Session-only (not persisted across restarts)

### Conversation Rewind
- Esc enters rewind mode when conversation exists
- ↑/↓ navigates user messages (visual highlighting)
- Enter truncates history at selected point, loads content into input
- Follows ChatGPT/Claude.ai pattern: truncate, don't branch

## Implementation

**State added to VirtualAgentApp:**
- `input_history: list[str]` - sent prompts
- `input_history_idx: int` - navigation position (-1 = draft)
- `input_draft: str` - preserved draft
- `rewind_mode: bool` - mode toggle
- `rewind_targets: list[tuple]` - (widget, history_idx, content)
- `rewind_selection: int` - current selection

**Key methods:**
- `action_history_prev/next()` - handles both input history and rewind nav
- `action_handle_escape()` - mode transitions
- `_enter/_exit_rewind_mode()` - visual state management
- `_execute_rewind()` - history truncation + UI cleanup

**CSS classes:** `.rewind-target`, `.rewind-selected`

## Completed

- [x] Input history state and navigation
- [x] Prompt recording on submit
- [x] Rewind mode with visual highlighting
- [x] History truncation and UI sync
- [x] Help text updated with new shortcuts
