# tui-011: Multi-line Input with External Editor

**Completed**: 2025-12-20

## Summary

Added dual-mode input system: single-line Input (Enter sends) by default, with Ctrl+E to open external editor for multi-line input.

## Design

**Dual-mode approach:**
- Default: `Input` widget, Enter submits immediately
- After Ctrl+E with multi-line content: `TextArea` widget, Ctrl+J submits
- After submit: returns to single-line mode

**Why this pattern:**
- Keeps simple case simple (Enter sends)
- Multi-line only when explicitly needed
- Uses user's preferred $EDITOR (vi default)
- Contextual hint via border subtitle

## Usage

| Mode | Widget | Send | Trigger |
|------|--------|------|---------|
| Single-line | Input | Enter | Default |
| Multi-line | TextArea | Ctrl+J | Ctrl+E with newlines |

## Implementation

- `tui.py`: Dual widget setup, mode switching, external editor integration
- `theme.py`: CSS for both Input and TextArea, `.hidden` class
- `commands.py`: Updated /help documentation

## Key Methods

- `_switch_to_multiline(content)`: Show TextArea with border hint
- `_switch_to_single_line()`: Return to Input
- `action_edit()`: Open $EDITOR, switch mode based on content
- `_submit_prompt(prompt)`: Shared submission logic
