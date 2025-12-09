# TUI Interface for Virtual Agent

A minimal, elegant terminal interface for the PydanticAI virtual filesystem agent.

## Overview

Textual-based TUI that wraps `virtual_agent.py`, providing:
- Clean input prompt for user messages
- Display of agent work (tool calls visible inline)
- Styled markdown output for agent responses
- Continuous conversation loop with history

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VirtualAgentApp                          │
│  (Textual App - manages layout, events, agent lifecycle)        │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│   Header        │ │  MessageLog     │ │  PromptInput            │
│   (Static)      │ │  (ScrollView +  │ │  (Input widget)         │
│   "Virtual OS"  │ │   Markdown)     │ │                         │
└─────────────────┘ └─────────────────┘ └─────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ agent.iter()    │
                    │ (PydanticAI)    │
                    └─────────────────┘
```

### Data Flow

```
User Input ──► on_input_submitted ──► agent.iter() ──► stream events
                                                            │
                  ┌─────────────────────────────────────────┘
                  ▼
         ┌───────────────────────────────────────────────┐
         │  For each node in agent_run:                  │
         │    - CallToolsNode → append tool call display │
         │    - End → finalize, re-enable input          │
         └───────────────────────────────────────────────┘
```

## File Structure

```
pydantic-agents/
├── virtual_agent.py      # Agent + VirtualFileSystem (library)
├── tui.py                # TUI consumer (imports from virtual_agent)
├── tui.tcss              # Textual CSS styles
└── pyproject.toml        # textual dependency
```

**Key principle:** `virtual_agent.py` is the library, `tui.py` is a thin view layer that imports from it. No code duplication.

## Design

### Color Palette (Monochrome + Accent)

- Background: `#0d0d0d` (near-black)
- Surface: `#1a1a1a` (header, input)
- Border: `#333333` (subtle)
- Text: `#e0e0e0` (primary)
- Accent: `#22c55e` (green - prompts, focus)
- Tool: `#3b82f6` (blue - tool calls)
- Error: `#ef4444` (red)

### Layout

1. **Vertical stack:** Header → Messages → Input (fixed at bottom)
2. **Full width:** No side panels
3. **Auto-scroll:** Messages scroll to bottom on new content

### Keybindings

- `ctrl+c` - Quit
- `ctrl+l` - Clear messages and history

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Import from `virtual_agent.py` | DRY - single source of truth for agent logic |
| Use `agent.iter()` | Full control over nodes, see tool calls |
| Monochrome + accent palette | Professional, reduces visual noise |

## Completed

- [x] Textual dependency added
- [x] TUI imports from virtual_agent (no duplication)
- [x] Tool calls displayed inline with styling
- [x] Message history for context continuity
- [x] Error handling (displays in red)
- [x] Clear action (ctrl+l)
