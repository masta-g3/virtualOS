# tui-002: Custom Theme System

**Status**: Complete
**Epic**: TUI
**Completed**: 2025-12-18

## Summary

Lightweight theming system inspired by Micro terminal editor. Users can select from 4 built-in themes or create custom ones via YAML files.

## What Was Built

- `theme.py` - Theme loader (~80 lines): `load_theme()`, `list_themes()`, `generate_css()`
- `settings.py` - Generic settings persistence (~25 lines)
- `themes/` - 4 built-in themes:
  - `amber-dark` (default) - warm amber on deep black
  - `catppuccin-macchiato` - soothing pastels
  - `gruvbox-dark` - retro earthy tones
  - `solarized-light` - low-contrast light mode

## Features

- [x] Hot-reload theme switching without restart
- [x] `/theme` - selector modal
- [x] `/theme <name>` - direct switch
- [x] `/theme list` - show available themes
- [x] Persistent settings at `~/.config/pyagents/settings.json`
- [x] User themes via `~/.config/pyagents/themes/`
- [x] Model and thinking level persistence (bonus)

## Theme Format

```yaml
name: theme-name
description: Short description

colors:
  bg_primary: "#hex"
  bg_surface: "#hex"
  text_primary: "#hex"
  text_secondary: "#hex"
  text_muted: "#hex"
  accent: "#hex"
  tool_call: "#hex"
  tool_result: "#hex"
  success: "#hex"
  error: "#hex"
  chrome: "#hex"
```

## Design Decisions

- **YAML over TOML**: More readable for color values, consistent with Micro's approach
- **Generated CSS over variables**: More reliable in Textual, easier to debug
- **Standalone themes**: No inheritance - keeps themes simple and self-contained
- **Generic settings module**: Single `settings.py` handles all preferences (theme, model, thinking)
