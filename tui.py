import json
import uuid
from pathlib import Path

from pydantic_ai import CallToolsNode, ModelMessagesTypeAdapter, ModelRequestNode, UsageLimits
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, Markdown, Static

from commands import dispatch
from virtual_agent import VirtualFileSystem, AgentDeps, agent

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


class VirtualAgentApp(App):
    """Minimal TUI for the virtual agent."""

    CSS_PATH = "tui.tcss"
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
            self.fs.files["/home/user/readme.txt"] = "Welcome to Virtual OS."

        self._snapshot = dict(self.fs.files)
        self.deps = AgentDeps(fs=self.fs, user_name="user", workspace_path=self.workspace_path)

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

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Static("Virtual OS", id="header-title")
            yield Static("", id="header-status")
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="prompt")
        yield Static("ctrl+s sync │ ctrl+l clear │ ctrl+c quit", id="footer")

    async def on_mount(self) -> None:
        self.query_one("#prompt", Input).focus()
        if self.history:
            await self._render_history()

    def on_unmount(self) -> None:
        if self.history:
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
                        await container.mount(Static(f"[#e6a855]┃[/] {part.content}", classes="user-message"))
                    elif isinstance(part, ToolReturnPart):
                        lines = str(part.content).split("\n")
                        for i, line in enumerate(lines):
                            prefix = "│ └─ " if i == 0 else "│    "
                            await container.mount(Static(f"{prefix}{line}", classes="tool-result", markup=False))
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        await container.mount(Static(f"│ ⚡ {part.tool_name}: {format_tool_args(part.args)}", classes="tool-call", markup=False))
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

        user_msg = Static(f"[#e6a855]┃[/] {prompt}", classes="user-message")
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
        async with agent.iter(
            prompt,
            deps=self.deps,
            message_history=self.history,
            usage_limits=UsageLimits(request_limit=10),
        ) as run:
            async for node in run:
                if isinstance(node, CallToolsNode):
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            tool_msg = Static(
                                f"│ ⚡ {part.tool_name}: {format_tool_args(part.args)}",
                                classes="tool-call",
                                markup=False,
                            )
                            await container.mount(tool_msg, before=response_widget)
                            container.scroll_end()
                elif isinstance(node, ModelRequestNode):
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            lines = str(part.content).split("\n")
                            for i, line in enumerate(lines):
                                prefix = "│ └─ " if i == 0 else "│    "
                                result_msg = Static(
                                    f"{prefix}{line}",
                                    classes="tool-result",
                                    markup=False,
                                )
                                await container.mount(result_msg, before=response_widget)
                            container.scroll_end()

            response_widget.update(f"╰ {run.result.output}")
            await container.mount(Static("", classes="turn-separator"))
            container.scroll_end()
            self.history = run.result.all_messages()
        self._check_modified()

    async def action_clear(self) -> None:
        """Start a new conversation (saves current one first)."""
        # Save current conversation before clearing
        if self.history:
            self.conversations[self.conversation_id] = {
                "messages": ModelMessagesTypeAdapter.dump_python(self.history, mode="json")
            }

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
        status.update(f"[#e6a855]{dot}[/] thinking...")
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

        # Save conversation history
        if self.history:
            self.conversations[self.conversation_id] = {
                "messages": ModelMessagesTypeAdapter.dump_python(self.history, mode="json")
            }
            save_chat_history(HISTORY_FILE, self.conversation_id, self.conversations)

        messages = self.query_one("#messages", VerticalScroll)
        confirm = Static(f"[Saved {count} files to {self.workspace_path}/]", classes="system-message")
        await messages.mount(confirm)
        messages.scroll_end()


def main():
    app = VirtualAgentApp()
    app.run()


if __name__ == "__main__":
    main()
