# TUI UX Improvements

**Feature ID**: tui-009
**Completed**: 2025-12-16

## Summary

Redesigned the TUI interface following Nielsen heuristics and modern UX principles while maintaining the project's minimalist philosophy. Applied a "Terminal Renaissance" aesthetic: warm amber palette, tree-style message threading, and animated feedback.

## Changes Implemented

### Phase 1: Quick Wins
- [x] Animated thinking indicator in header (right-aligned status zone)
- [x] Keybinding footer (`ctrl+s save │ ctrl+l new │ ctrl+c quit`)
- [x] Warm amber color palette replacing generic green

### Phase 2: Visual Hierarchy
- [x] Tree-style message prefixes: `┃` user, `│ ⚡` tool, `│ └─` result, `╰` agent
- [x] Turn separators between conversation rounds
- [x] `format_tool_args()` helper for cleaner command display

### Phase 3: Motion
- [x] Rotating thinking animation (`◐◓◑◒` at 150ms intervals)
- [~] Message transitions deferred (Textual limitation)

## Visual Result

```
┌─────────────────────────────────────────────────────────────┐
│ Virtual OS                                    ◐ thinking... │
├─────────────────────────────────────────────────────────────┤
│ ┃ list files                                                │
│ │ ⚡ run_shell: ls                                          │
│ │ └─ readme.txt                                             │
│ │    script.py                                              │
│ ╰ Found 2 files in your directory...                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Type a message...                                           │
├─────────────────────────────────────────────────────────────┤
│        ctrl+s save │ ctrl+l new │ ctrl+c quit               │
└─────────────────────────────────────────────────────────────┘
```

## Design Decisions

- **Amber over green**: Warmer, more intentional accent color
- **Tree connectors**: Visual threading without additional UI complexity
- **Animation in header only**: Minimal motion where it matters (system status)
- **Message transitions skipped**: Textual lacks CSS transitions; programmatic approach adds complexity without proportional benefit

## Files Modified

- `tui.py` — header split, animation timer, tree prefixes, format helper
- `tui.tcss` — warm palette, header/footer styles, separator class
