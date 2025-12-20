"""Slash command system for the TUI."""

from dataclasses import dataclass
from typing import Callable, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    from tui import VirtualAgentApp

REGISTRY: dict[str, "CommandInfo"] = {}


@dataclass
class CommandInfo:
    name: str
    handler: Callable[["VirtualAgentApp", str], Awaitable[str | None]]
    help: str
    usage: str | None = None


def command(name: str, help: str, usage: str | None = None):
    """Decorator to register a slash command."""
    def decorator(fn: Callable[["VirtualAgentApp", str], Awaitable[str | None]]):
        REGISTRY[name] = CommandInfo(name, fn, help, usage)
        return fn
    return decorator


async def dispatch(app: "VirtualAgentApp", raw_input: str) -> str | None:
    """Parse and execute a slash command. Returns output or None if silent."""
    content = raw_input[1:].strip()
    if not content:
        return "Type /help for available commands."

    parts = content.split(maxsplit=1)
    cmd_name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd_name not in REGISTRY:
        return f"Unknown command: /{cmd_name}. Type /help for available commands."

    return await REGISTRY[cmd_name].handler(app, args)


# ─────────────────────────────────────────────────────────────
# Built-in Commands
# ─────────────────────────────────────────────────────────────

@command("help", help="List available commands")
async def cmd_help(app: "VirtualAgentApp", args: str) -> str:
    lines = ["**Available commands:**", ""]
    for name, info in sorted(REGISTRY.items()):
        usage = info.usage or f"/{name}"
        lines.append(f"- `{usage}` — {info.help}")
    lines.extend([
        "",
        "**Input:** Enter sends. Use Ctrl+E for multi-line (opens $EDITOR).",
        "",
        "**Keyboard shortcuts:**",
        "- `Ctrl+C` — Quit",
        "- `Ctrl+E` — Open $EDITOR (multi-line mode, Ctrl+J to send)",
        "- `Ctrl+L` — Clear (new session)",
        "- `Ctrl+S` — Save workspace",
        "- `Ctrl+Y` — Copy mode (1-9 to select block)",
    ])
    return "\n".join(lines)


@command("clear", help="Save conversation and start fresh")
async def cmd_clear(app: "VirtualAgentApp", args: str) -> str | None:
    await app.action_clear()
    return None


@command("sync", help="Save workspace files to disk")
async def cmd_sync(app: "VirtualAgentApp", args: str) -> str | None:
    await app.action_save()
    return None


@command("model", help="Select or switch model", usage="/model [NAME]")
async def cmd_model(app: "VirtualAgentApp", args: str) -> str | None:
    args = args.strip()

    if not args:
        app.show_model_selector()
        return None

    return app.switch_model(args)


@command("thinking", help="Select thinking effort level", usage="/thinking [LEVEL]")
async def cmd_thinking(app: "VirtualAgentApp", args: str) -> str | None:
    args = args.strip()

    if not args:
        app.show_thinking_selector()
        return None

    level = None if args == "off" else args
    return app.set_thinking(level)


@command("quit", help="Exit the application")
async def cmd_quit(app: "VirtualAgentApp", args: str) -> None:
    app.exit()


@command("files", help="List files in virtual filesystem")
async def cmd_files(app: "VirtualAgentApp", args: str) -> str:
    files = app.fs.files
    if not files:
        return "Virtual filesystem is empty."

    lines = ["**Virtual filesystem:**", ""]
    for path in sorted(files.keys()):
        size = len(files[path])
        lines.append(f"- `{path}` ({size} chars)")
    return "\n".join(lines)


@command("sessions", help="Browse previous sessions (d to delete)")
async def cmd_sessions(app: "VirtualAgentApp", args: str) -> str | None:
    app.show_sessions_selector()
    return None


@command("theme", help="Select or switch theme", usage="/theme [NAME|list]")
async def cmd_theme(app: "VirtualAgentApp", args: str) -> str | None:
    args = args.strip()

    if not args:
        app.show_theme_selector()
        return None

    if args == "list":
        from theme import list_themes
        themes = list_themes()
        lines = ["**Themes:**", ""]
        for t in themes:
            marker = "→ " if t == app.theme_name else "  "
            lines.append(f"{marker}`{t}`")
        return "\n".join(lines)

    return app.switch_theme(args)
