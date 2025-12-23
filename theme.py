"""Lightweight theme loader for the TUI."""
from dataclasses import dataclass
from pathlib import Path

import yaml

THEMES_DIR = Path(__file__).parent / "themes"
USER_THEMES_DIR = Path.home() / ".config" / "pyagents" / "themes"
DEFAULT_THEME = "amber-dark"

REQUIRED_COLORS = {
    "bg_primary", "bg_surface",
    "text_primary", "text_secondary", "text_muted",
    "accent", "tool_call", "tool_result", "success", "error", "chrome"
}


@dataclass
class Theme:
    name: str
    description: str
    colors: dict[str, str]


def load_theme(name: str) -> Theme:
    """Load theme by name from built-in or user directory."""
    user_path = USER_THEMES_DIR / f"{name}.yaml"
    builtin_path = THEMES_DIR / f"{name}.yaml"

    path = user_path if user_path.exists() else builtin_path
    if not path.exists():
        raise FileNotFoundError(f"Theme not found: {name}")

    data = yaml.safe_load(path.read_text())

    missing = REQUIRED_COLORS - set(data.get("colors", {}).keys())
    if missing:
        raise ValueError(f"Theme {name} missing colors: {missing}")

    return Theme(
        name=data["name"],
        description=data.get("description", ""),
        colors=data["colors"]
    )


def list_themes() -> list[str]:
    """List available theme names."""
    themes = set()
    for dir in [THEMES_DIR, USER_THEMES_DIR]:
        if dir.exists():
            themes.update(p.stem for p in dir.glob("*.yaml"))
    return sorted(themes)


def generate_css(theme: Theme) -> str:
    """Generate Textual CSS from theme colors."""
    c = theme.colors
    return f'''/* Auto-generated from theme: {theme.name} */

Screen {{
    background: {c["bg_primary"]};
}}

#header {{
    dock: top;
    height: 1;
    background: {c["bg_surface"]};
    padding: 0 1;
}}

#header-title {{
    color: {c["accent"]};
    text-style: bold;
    width: auto;
}}

#header-status {{
    color: {c["accent"]};
    text-align: right;
    width: 1fr;
}}

#messages {{
    padding: 1;
    scrollbar-size: 1 1;
    scrollbar-background: {c["bg_surface"]};
    scrollbar-color: {c["chrome"]};
}}

.user-message {{
    height: auto;
    margin: 0 0 1 0;
}}

.agent-message {{
    color: {c["text_secondary"]};
    margin: 0 0 2 0;
    padding: 0;
}}

.tool-call {{
    color: {c["tool_call"]};
    margin: 0;
}}

.tool-result {{
    color: {c["tool_result"]};
    margin: 0;
}}

.error-message {{
    color: {c["error"]};
}}

.system-message {{
    color: {c["success"]};
    text-style: italic;
    margin: 0 0 1 0;
}}

Input#prompt-single {{
    dock: bottom;
    height: 3;
    margin: 0 1 1 1;
    background: {c["bg_surface"]};
    border: tall {c["chrome"]};
    padding: 0 1;
}}

Input#prompt-single:focus {{
    border: tall {c["accent"]};
}}

TextArea#prompt-multi {{
    dock: bottom;
    height: auto;
    min-height: 3;
    max-height: 8;
    margin: 0 1 1 1;
    background: {c["bg_surface"]};
    border: tall {c["chrome"]};
    padding: 0 1;
}}

TextArea#prompt-multi:focus {{
    border: tall {c["accent"]};
}}

TextArea#prompt-multi .text-area--cursor {{
    background: {c["accent"]};
}}

TextArea#prompt-multi .text-area--placeholder {{
    color: {c["text_muted"]};
}}

.hidden {{
    display: none;
}}

SelectorScreen {{
    align: center middle;
    background: rgba(10, 10, 11, 0.85);
}}

#selector-title {{
    color: {c["accent"]};
    text-style: bold;
    padding: 0 0 1 0;
    text-align: center;
}}

#selector-list {{
    width: auto;
    min-width: 40;
    max-height: 12;
    background: {c["bg_surface"]};
    border: round {c["chrome"]};
    padding: 0 1;
}}

#selector-list:focus {{
    border: round {c["accent"]};
}}

#selector-list > .option-list--option-highlighted {{
    background: {c["bg_primary"]};
    color: {c["accent"]};
}}

.copy-target {{
    border: round {c["accent"]};
}}

.rewind-target {{
    opacity: 0.6;
}}

.rewind-selected {{
    opacity: 1.0;
    border: tall {c["accent"]};
    background: {c["bg_surface"]};
}}
'''
