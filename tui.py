import json
import uuid
from pathlib import Path

from pydantic_ai import CallToolsNode, ModelMessagesTypeAdapter, ModelRequestNode, UsageLimits
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown, Static

from virtual_agent import VirtualFileSystem, AgentDeps, agent

WORKSPACE_PATH = Path("./workspace")
HISTORY_FILE = WORKSPACE_PATH / ".chat_history.json"


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
        yield Static("Virtual OS", id="header")
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="prompt")

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
                        await container.mount(Static(f"> {part.content}", classes="user-message"))
                    elif isinstance(part, ToolReturnPart):
                        content = str(part.content).replace("\n", "\n      ")
                        await container.mount(Static(f"    → {content}", classes="tool-result", markup=False))
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        await container.mount(Static(f"  [{part.tool_name}] {part.args}", classes="tool-call", markup=False))
                    elif isinstance(part, TextPart):
                        await container.mount(Markdown(part.content, classes="agent-message"))
        container.scroll_end()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return

        input_widget = self.query_one("#prompt", Input)
        input_widget.value = ""
        input_widget.disabled = True

        messages = self.query_one("#messages", VerticalScroll)

        user_msg = Static(f"> {prompt}", classes="user-message")
        await messages.mount(user_msg)
        messages.scroll_end()

        response = Markdown("", classes="agent-message")
        await messages.mount(response)

        try:
            await self._run_agent(prompt, response, messages)
        except Exception as e:
            response.update(f"**Error:** {e}")
            response.add_class("error-message")

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
                                f"  [{part.tool_name}] {part.args}",
                                classes="tool-call",
                                markup=False,
                            )
                            await container.mount(tool_msg, before=response_widget)
                            container.scroll_end()
                elif isinstance(node, ModelRequestNode):
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            content = str(part.content).replace("\n", "\n      ")
                            result_msg = Static(
                                f"    → {content}",
                                classes="tool-result",
                                markup=False,
                            )
                            await container.mount(result_msg, before=response_widget)
                            container.scroll_end()

            response_widget.update(run.result.output)
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

    def _update_header(self) -> None:
        """Update header to show modified status."""
        header = self.query_one("#header", Static)
        if self.modified:
            header.update("Virtual OS [modified]")
        else:
            header.update("Virtual OS")

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
