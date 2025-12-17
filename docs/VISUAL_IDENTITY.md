# Visual Identity

Design system for the Virtual OS TUI. Follow these guidelines to maintain visual consistency.

## Philosophy

**"Terminal Renaissance"** — Blend classic terminal precision with modern refinement. Professional, focused, subtly sophisticated. Not flashy, not boring.

Core principles:
- **Intentionality over decoration** — Every visual element serves a purpose
- **Warmth over sterility** — Amber accents humanize the interface
- **Hierarchy through typography** — Prefixes and spacing, not boxes and borders
- **Motion with restraint** — Animate only system status, not content

## Color Palette

```
┌─────────────────────────────────────────────────────────────┐
│  BACKGROUNDS                                                │
│  ──────────                                                 │
│  #0a0a0b  ████  Deep black (screen base)                    │
│  #141416  ████  Surface (header, input)                     │
│                                                             │
│  TEXT                                                       │
│  ────                                                       │
│  #e8e6e3  ████  Primary (user messages)                     │
│  #9a9894  ████  Secondary (agent responses)                 │
│  #5c5a56  ████  Muted (footer, hints)                       │
│                                                             │
│  ACCENT                                                     │
│  ──────                                                     │
│  #e6a855  ████  Amber (header, focus, user prefix)          │
│                                                             │
│  SEMANTIC                                                   │
│  ────────                                                   │
│  #7aa2f7  ████  Tool calls (soft blue)                      │
│  #6b7280  ████  Tool results (neutral gray)                 │
│  #5ce888  ████  Success/system messages (green)             │
│  #e85c5c  ████  Errors (red)                                │
│                                                             │
│  CHROME                                                     │
│  ──────                                                     │
│  #3a3a3d  ████  Borders, scrollbars                         │
└─────────────────────────────────────────────────────────────┘
```

### Usage Rules

| Element | Color | Rationale |
|---------|-------|-----------|
| User input | `#e8e6e3` | Highest contrast, user's words matter most |
| Agent response | `#9a9894` | Secondary, let user content stand out |
| Tool calls | `#7aa2f7` | Blue = action/process (universal convention) |
| Tool results | `#6b7280` | Lowest priority, supporting info |
| Focus states | `#e6a855` | Amber draws attention without alarm |
| Errors | `#e85c5c` | Red = problem (universal convention) |

## Visual Hierarchy

### Message Prefixes

Use Unicode box-drawing characters to create visual threading:

```
┃ User message                          ← Thick bar (amber)
│ ⚡ run_shell: ls                       ← Tool call (blue)
│ └─ file1.txt                          ← First result line
│    file2.txt                          ← Continuation
╰ Agent response in markdown...         ← Curved end (gray)
```

| Prefix | Unicode | Purpose |
|--------|---------|---------|
| `┃` | U+2503 | User message start (colored amber) |
| `│` | U+2502 | Vertical connector |
| `⚡` | U+26A1 | Tool execution indicator |
| `└─` | U+2514 + U+2500 | First line of tool result |
| `╰` | U+256E | Agent response start |

### Spacing

- **Turn separator**: Empty line between conversation rounds
- **No margin** on tool calls/results (prefixes provide structure)
- **1-line margin** below user messages and agent responses

## Typography

Textual renders in the user's terminal emulator—we can't force fonts. Design for common monospace fonts:

**Recommended terminal fonts** (suggest in docs):
- JetBrains Mono
- Berkeley Mono
- Iosevka
- SF Mono

**Unicode requirements**: Ensure chosen font supports box-drawing (U+2500-257F) and symbols (⚡).

## Motion

### Thinking Animation

Rotating quarter-circle at 150ms intervals:

```
◐ → ◓ → ◑ → ◒ → (repeat)
```

Located in header status zone (right-aligned). Amber colored.

### When to Animate

| Scenario | Animation | Rationale |
|----------|-----------|-----------|
| Agent processing | Rotating indicator | System status visibility |
| Message arrival | None | Content should appear instantly |
| Errors | None | Static red is enough |
| Saving | None | Brief action, confirmation message suffices |

**Rule**: Animate waiting states, not content delivery.

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER: title (left) + status zone (right)         height: 1│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ MESSAGES: scrollable conversation area              flex: 1 │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ INPUT: text field with focus border                height: 3│
├─────────────────────────────────────────────────────────────┤
│ FOOTER: keybinding hints (centered, muted)         height: 1│
└─────────────────────────────────────────────────────────────┘
```

### Header Status Zone

Right side of header displays (in priority order):
1. `◐ thinking...` — During agent processing
2. `[modified]` — Unsaved filesystem changes
3. (empty) — Idle state

Only one status shown at a time. Thinking takes precedence.

## Do's and Don'ts

### Do

- Use the established prefix system for new message types
- Keep animations in the header/status area only
- Use amber for interactive elements (focus, user prefix)
- Let content breathe with turn separators
- Test with common terminal fonts

### Don't

- Add new accent colors (amber + blue + semantic covers all cases)
- Animate message content or tool output
- Use borders/boxes around messages (prefixes provide structure)
- Add icons beyond `⚡` for tools (keep vocabulary minimal)
- Use green for non-success states (reserved for confirmations)

## Extending the System

### Adding a New Message Type

1. Choose appropriate prefix from existing vocabulary
2. Use existing color from semantic palette
3. Follow spacing conventions (no margin for inline, 1-line for blocks)
4. No new CSS classes unless truly necessary

### Adding a New Status Indicator

1. Must fit in header status zone (right side)
2. Define priority relative to existing states
3. Use amber for active states, muted for passive
4. Keep text short (header is single line)

---

*This document describes the implemented visual system as of tui-009. Update when design evolves.*
