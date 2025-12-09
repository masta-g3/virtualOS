from pydantic_ai import CallToolsNode, UsageLimits
from pydantic_ai.messages import ModelMessage, ToolCallPart
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown, Static

from virtual_agent import VirtualFileSystem, AgentDeps, agent


class VirtualAgentApp(App):
    """Minimal TUI for the virtual agent."""

    CSS_PATH = "tui.tcss"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
    ]

    def __init__(self):
        super().__init__()
        self.fs = VirtualFileSystem()
        self.fs.files["/home/user/readme.txt"] = "Welcome to Virtual OS."
        self.deps = AgentDeps(fs=self.fs, user_name="user")
        self.history: list[ModelMessage] = []

    def compose(self) -> ComposeResult:
        yield Static("Virtual OS", id="header")
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="prompt")

    def on_mount(self) -> None:
        self.query_one("#prompt", Input).focus()

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
            usage_limits=UsageLimits(request_limit=25),
        ) as run:
            async for node in run:
                if isinstance(node, CallToolsNode):
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            tool_msg = Static(
                                f"  [{part.tool_name}] {part.args}",
                                classes="tool-call",
                            )
                            await container.mount(tool_msg, before=response_widget)
                            container.scroll_end()

            response_widget.update(run.result.output)
            container.scroll_end()
            self.history = run.result.all_messages()

    async def action_clear(self) -> None:
        """Clear message history."""
        messages = self.query_one("#messages", VerticalScroll)
        await messages.remove_children()
        self.history = []


def main():
    app = VirtualAgentApp()
    app.run()


if __name__ == "__main__":
    main()
