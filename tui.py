import json
import uuid
from pathlib import Path

from pydantic_ai import CallToolsNode, ModelMessagesTypeAdapter, ModelRequestNode, UsageLimits
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Markdown, OptionList, Static
from textual.widgets.option_list import Option

from commands import dispatch
import settings
from theme import load_theme, list_themes, generate_css, DEFAULT_THEME
from virtual_agent import VirtualFileSystem, AgentDeps, create_agent, MODELS, ThinkingEffort, VIRTUAL_ROOT

WORKSPACE_PATH = Path("./workspace")
HISTORY_FILE = WORKSPACE_PATH / ".chat_history.json"


def format_tool_args(args) -> str:
    """Extract clean command from tool args."""
    # Handle dict
    if isinstance(args, dict) and "command" in args:
        return args["command"]
    # Handle JSON string
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            if isinstance(parsed, dict) and "command" in parsed:
                return parsed["command"]
        except json.JSONDecodeError:
            pass
    return str(args)


def load_chat_history(path: Path) -> tuple[str, dict]:
    """Load history file, return (current_id, conversations dict)."""
    if path.exists():
        data = json.loads(path.read_text())
        return data.get("current"), data.get("conversations", {})
    return None, {}


def save_chat_history(path: Path, current_id: str, conversations: dict) -> None:
    """Save history to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"current": current_id, "conversations": conversations}))


def format_tool_result(content: str) -> list[Static]:
    """Format tool result content into prefixed Static widgets."""
    lines = str(content).split("\n")
    return [
        Static(f"{'│ └─ ' if i == 0 else '│    '}{line}", classes="tool-result", markup=False)
        for i, line in enumerate(lines)
    ]


def format_tool_call(part: ToolCallPart) -> Static:
    """Format a tool call into a Static widget."""
    return Static(f"│ ⚡ {part.tool_name}: {format_tool_args(part.args)}", classes="tool-call", markup=False)


class SelectorScreen(ModalScreen[str | None]):
    """Modal selector for models/thinking levels. Returns selected key or None on ESC."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, options: list[tuple[str, str]], current: str | None = None):
        super().__init__()
        self.title = title
        self.options = options
        self.current = current

    def compose(self) -> ComposeResult:
        yield Static(f"[b]{self.title}[/b]", id="selector-title")
        option_list = OptionList(id="selector-list")
        for key, label in self.options:
            marker = "→ " if key == self.current else "  "
            option_list.add_option(Option(f"{marker}{label}", id=key))
        yield option_list

    def on_mount(self) -> None:
        self.query_one("#selector-list", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class VirtualAgentApp(App):
    """Minimal TUI for the virtual agent."""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self):
        super().__init__()
        self.fs = VirtualFileSystem()
        self.workspace_path = WORKSPACE_PATH
        self.modified = False
        self.thinking = False
        self._thinking_timer = None
        self._thinking_frame = 0

        count = self.fs.load_from_disk(self.workspace_path)
        if count == 0:
            self.fs.files[f"{VIRTUAL_ROOT}/readme.txt"] = "Welcome to Virtual OS."

        self._snapshot = dict(self.fs.files)
        self.deps = AgentDeps(fs=self.fs, user_name="user", workspace_path=self.workspace_path)

        # Load persisted settings
        self.current_model = settings.get("model", "openai")
        self.thinking_effort: ThinkingEffort = settings.get("thinking", "high")
        self.theme_name = settings.get("theme", DEFAULT_THEME)

        self.agent = create_agent(self.current_model, self.thinking_effort)
        self._theme = load_theme(self.theme_name)

        # Load or create conversation
        current_id, conversations = load_chat_history(HISTORY_FILE)
        if current_id and current_id in conversations:
            self.conversation_id = current_id
            self.history = ModelMessagesTypeAdapter.validate_python(
                conversations[current_id]["messages"]
            )
        else:
            self.conversation_id = str(uuid.uuid4())
            self.history = []
        self.conversations = conversations

    def switch_theme(self, name: str) -> str:
        """Switch to a different theme. Returns status message."""
        available = list_themes()
        if name not in available:
            return f"Unknown theme: {name}. Available: {', '.join(available)}"

        self._theme = load_theme(name)
        self.theme_name = name
        settings.set("theme", name)

        # Replace CSS source and reapply to all widgets
        self.stylesheet.add_source(generate_css(self._theme), read_from="theme")
        self.stylesheet.reparse()
        self.stylesheet.update(self)
        self.refresh(layout=True)
        return f"Theme: {name}"

    def show_theme_selector(self) -> None:
        """Show theme selector modal."""
        themes = list_themes()
        options = [(t, t) for t in themes]
        self.push_screen(
            SelectorScreen("Select Theme", options, self.theme_name),
            callback=self._on_theme_selected
        )

    def _on_theme_selected(self, selected: str | None) -> None:
        """Handle theme selection result."""
        if selected and selected != self.theme_name:
            msg = self.switch_theme(selected)
            self._show_system_message(msg)

    def switch_model(self, model_key: str) -> str:
        """Switch to a different model. Returns status message."""
        if model_key not in MODELS:
            return f"Unknown model: {model_key}. Available: {', '.join(MODELS.keys())}"

        self.current_model = model_key
        self.agent = create_agent(model_key, self.thinking_effort)
        settings.set("model", model_key)
        return f"Switched to {model_key}"

    def set_thinking(self, level: ThinkingEffort) -> str:
        """Set thinking effort level. Returns status message."""
        valid = {"low", "medium", "high", None}
        if level not in valid:
            return f"Invalid level. Use: low, medium, high, or off"

        self.thinking_effort = level
        self.agent = create_agent(self.current_model, self.thinking_effort)
        settings.set("thinking", level)
        return f"Thinking effort: {level or 'off'}"

    def show_model_selector(self) -> None:
        """Show model selector modal."""
        options = [(key, f"{key} ({model_id})") for key, model_id in MODELS.items()]
        self.push_screen(
            SelectorScreen("Select Model", options, self.current_model),
            callback=self._on_model_selected
        )

    def _on_model_selected(self, selected: str | None) -> None:
        """Handle model selection result."""
        if selected and selected != self.current_model:
            msg = self.switch_model(selected)
            self._show_system_message(msg)

    def show_thinking_selector(self) -> None:
        """Show thinking level selector modal."""
        options = [("high", "high"), ("medium", "medium"), ("low", "low"), ("off", "off")]
        current = self.thinking_effort or "off"
        self.push_screen(
            SelectorScreen("Thinking Effort", options, current),
            callback=self._on_thinking_selected
        )

    def _on_thinking_selected(self, selected: str | None) -> None:
        """Handle thinking level selection result."""
        if selected:
            level = None if selected == "off" else selected
            if level != self.thinking_effort:
                msg = self.set_thinking(level)
                self._show_system_message(msg)

    def _show_system_message(self, msg: str) -> None:
        """Show a system message in the chat."""
        messages = self.query_one("#messages", VerticalScroll)
        messages.mount(Static(f"[{msg}]", classes="system-message"))
        messages.scroll_end()

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Static("Virtual OS", id="header-title")
            yield Static("", id="header-status")
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="prompt")

    async def on_mount(self) -> None:
        # Apply theme CSS (css property isn't auto-loaded)
        self.stylesheet.add_source(generate_css(self._theme), read_from="theme")
        self.stylesheet.reparse()
        self.stylesheet.update(self)

        self.query_one("#prompt", Input).focus()
        if self.history:
            await self._render_history()

    def on_unmount(self) -> None:
        self._persist_conversation()

    def _persist_conversation(self) -> None:
        """Save current conversation to history dict and disk."""
        if not self.history:
            return
        self.conversations[self.conversation_id] = {
            "messages": ModelMessagesTypeAdapter.dump_python(self.history, mode="json")
        }
        save_chat_history(HISTORY_FILE, self.conversation_id, self.conversations)

    async def _render_history(self) -> None:
        """Re-render conversation history into the UI."""
        container = self.query_one("#messages", VerticalScroll)
        for msg in self.history:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        accent = self._theme.colors["accent"]
                        await container.mount(Static(f"[{accent}]┃[/] {part.content}", classes="user-message"))
                    elif isinstance(part, ToolReturnPart):
                        for widget in format_tool_result(part.content):
                            await container.mount(widget)
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        await container.mount(format_tool_call(part))
                    elif isinstance(part, TextPart):
                        await container.mount(Markdown(f"╰ {part.content}", classes="agent-message"))
                        await container.mount(Static("", classes="turn-separator"))
        container.scroll_end()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return

        input_widget = self.query_one("#prompt", Input)
        input_widget.value = ""

        messages = self.query_one("#messages", VerticalScroll)

        if prompt.startswith("/"):
            result = await dispatch(self, prompt)
            if result:
                await messages.mount(Markdown(result, classes="agent-message"))
                messages.scroll_end()
            input_widget.focus()
            return

        input_widget.disabled = True

        accent = self._theme.colors["accent"]
        user_msg = Static(f"[{accent}]┃[/] {prompt}", classes="user-message")
        await messages.mount(user_msg)
        messages.scroll_end()

        response = Markdown("", classes="agent-message")
        await messages.mount(response)

        self._set_thinking(True)
        try:
            await self._run_agent(prompt, response, messages)
        except Exception as e:
            response.update(f"**Error:** {e}")
            response.add_class("error-message")
        finally:
            self._set_thinking(False)

        input_widget.disabled = False
        input_widget.focus()

    async def _run_agent(
        self,
        prompt: str,
        response_widget: Markdown,
        container: VerticalScroll,
    ) -> None:
        """Run agent with streaming and tool visibility."""
        async with self.agent.iter(
            prompt,
            deps=self.deps,
            message_history=self.history,
            usage_limits=UsageLimits(request_limit=10),
        ) as run:
            async for node in run:
                if isinstance(node, CallToolsNode):
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            await container.mount(format_tool_call(part), before=response_widget)
                            container.scroll_end()
                elif isinstance(node, ModelRequestNode):
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            for widget in format_tool_result(part.content):
                                await container.mount(widget, before=response_widget)
                            container.scroll_end()

            response_widget.update(f"╰ {run.result.output}")
            await container.mount(Static("", classes="turn-separator"))
            container.scroll_end()
            self.history = run.result.all_messages()
        self._check_modified()

    async def action_clear(self) -> None:
        """Start a new conversation (saves current one first)."""
        self._persist_conversation()
        # Start new conversation
        self.conversation_id = str(uuid.uuid4())
        self.history = []

        messages = self.query_one("#messages", VerticalScroll)
        await messages.remove_children()

    def _set_thinking(self, thinking: bool) -> None:
        """Set thinking state and start/stop animation."""
        self.thinking = thinking
        if thinking:
            self._thinking_frame = 0
            self._thinking_timer = self.set_interval(0.15, self._animate_thinking)
        else:
            if self._thinking_timer:
                self._thinking_timer.stop()
                self._thinking_timer = None
            self._update_header()

    def _animate_thinking(self) -> None:
        """Cycle through thinking animation frames."""
        frames = ["◐", "◓", "◑", "◒"]
        status = self.query_one("#header-status", Static)
        dot = frames[self._thinking_frame % len(frames)]
        accent = self._theme.colors["accent"]
        status.update(f"[{accent}]{dot}[/] thinking...")
        self._thinking_frame += 1

    def _update_header(self) -> None:
        """Update header status (right side)."""
        status = self.query_one("#header-status", Static)
        if self.thinking:
            return  # Animation handles this
        elif self.modified:
            status.update("[modified]")
        else:
            status.update("")

    def _check_modified(self) -> None:
        """Check if filesystem differs from snapshot."""
        self.modified = self.fs.files != self._snapshot
        self._update_header()

    async def action_save(self) -> None:
        """Save workspace and conversation to disk."""
        count = self.fs.save_to_disk(self.workspace_path)
        self._snapshot = dict(self.fs.files)
        self.modified = False
        self._update_header()

        self._persist_conversation()

        messages = self.query_one("#messages", VerticalScroll)
        confirm = Static(f"[Saved {count} files to {self.workspace_path}/]", classes="system-message")
        await messages.mount(confirm)
        messages.scroll_end()


def main():
    app = VirtualAgentApp()
    app.run()


if __name__ == "__main__":
    main()
