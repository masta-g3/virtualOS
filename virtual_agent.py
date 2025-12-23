import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from typing import Literal

from dotenv import load_dotenv

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent, PartDeltaEvent, ThinkingPartDelta
from pydantic_ai.models.anthropic import AnthropicModelSettings
from pydantic_ai.models.google import GoogleModelSettings
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

load_dotenv()

VIRTUAL_ROOT = "/home/user"

MODELS: dict[str, str] = {
    "openai": "openai-responses:gpt-5.1-codex-mini",
    "gemini": "google-gla:gemini-3-flash-preview",
    "haiku": "anthropic:claude-haiku-4-5",
}

ThinkingEffort = Literal["low", "medium", "high"] | None

ANTHROPIC_BUDGET = {"low": 1024, "medium": 4096, "high": 16384}


def _build_settings(model_key: str, thinking_effort: ThinkingEffort):
    """Build model-specific settings from unified thinking_effort."""
    if model_key == "openai":
        return OpenAIResponsesModelSettings(
            openai_reasoning_summary="detailed",
            openai_reasoning_effort=thinking_effort or "none",
        )

    if model_key == "gemini":
        return GoogleModelSettings(
            google_thinking_config={"thinking_level": thinking_effort or "minimal"}
        )

    if model_key == "haiku":
        if thinking_effort:
            budget = ANTHROPIC_BUDGET[thinking_effort]
            return AnthropicModelSettings(
                max_tokens=budget + 8192,
                anthropic_thinking={"type": "enabled", "budget_tokens": budget}
            )
        return None

    return None


@dataclass
class VirtualFileSystem:
    """In-memory filesystem. Data is lost when the script ends."""

    files: dict[str, str] = field(default_factory=dict)
    cwd: str = VIRTUAL_ROOT

    def _resolve(self, path: str) -> str:
        if path.startswith("/"):
            resolved = path
        else:
            resolved = f"{self.cwd.rstrip('/')}/{path}"
        # Normalize . and ..
        parts = []
        for part in resolved.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        return "/" + "/".join(parts)

    def write(self, path: str, content: str) -> str:
        full_path = self._resolve(path)
        self.files[full_path] = content
        return f"Successfully wrote {len(content)} chars to {full_path}"

    def read(self, path: str) -> str:
        full_path = self._resolve(path)
        if full_path not in self.files:
            return f"Error: File {full_path} does not exist."
        return self.files[full_path]

    def list_dir(self, path: str = ".") -> str:
        target_dir = self._resolve(path)
        matches = []
        for file_path in self.files:
            if file_path.startswith(target_dir):
                relative = file_path[len(target_dir) :].lstrip("/")
                if "/" not in relative:
                    matches.append(relative)
        if not matches:
            return "(empty directory)"
        return "\n".join(matches)

    def delete(self, path: str) -> str:
        full_path = self._resolve(path)
        if full_path in self.files:
            del self.files[full_path]
            return f"Deleted {full_path}"
        return f"Error: File {full_path} not found"

    def load_from_disk(self, host_path: Path, virtual_root: str = VIRTUAL_ROOT) -> int:
        """Load files from host folder into virtual filesystem. Returns count."""
        count = 0
        if not host_path.exists():
            return count
        for file in host_path.rglob("*"):
            if file.is_file():
                try:
                    content = file.read_text()
                    relative = file.relative_to(host_path)
                    virtual_path = f"{virtual_root}/{relative}"
                    self.files[virtual_path] = content
                    count += 1
                except (UnicodeDecodeError, PermissionError):
                    pass
        return count

    def save_to_disk(self, host_path: Path, virtual_root: str = VIRTUAL_ROOT) -> int:
        """Save virtual files back to host folder. Returns count."""
        count = 0
        host_path.mkdir(parents=True, exist_ok=True)
        for virtual_path, content in self.files.items():
            if virtual_path.startswith(virtual_root):
                relative = virtual_path[len(virtual_root):].lstrip("/")
                if relative:
                    target = host_path / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)
                    count += 1
        return count


@dataclass
class AgentDeps:
    fs: VirtualFileSystem
    user_name: str
    workspace_path: Path | None = None


SYSTEM_PROMPT = """\
You are a research assistant with access to the LLMpedia arXiv paper database.

## Tools

File operations:
- write_file(path, content): Create or overwrite a file
- read_file(path): Read file contents
- run_shell(command): Shell commands (ls, rm, pwd, cd, python)

Research tools:
- search_arxiv(...): Search papers by semantic query, title, author, date filters
- get_paper_summaries(codes, resolution): Get summaries at low/medium/high detail
- fetch_paper(code): Download full paper markdown to /home/user/papers/

## Research Workflow

### Two Modes

**Narrow/Deep** (1-3 papers, need details):
- Skip summaries, fetch full papers directly
- Example: "Find the original attention paper" → download and read

**Broad/Survey** (5+ papers, need overview):
- Start with low/medium summaries, triage, then escalate selectively
- Example: "RLHF advances?" → summaries first → drill into 2-3

### Escalation Path
low summary → medium → high → full paper

### Flow
1. DISCOVER: search_arxiv with appropriate filters
2. EVALUATE: Choose narrow/deep or broad/survey path
3. ESCALATE: Only fetch full papers when summaries aren't enough
4. ITERATE: Refine queries, follow interesting threads
5. SYNTHESIZE: Review scratchpad, cite papers with arxiv codes

## Scratchpad

Maintain /home/user/scratchpad.md to accumulate findings:
- Create with write_file on first use (don't read if it doesn't exist yet)
- Append new findings
- write_file to save updates
"""


def write_file(ctx: RunContext[AgentDeps], path: str, content: str) -> str:
    """
    Write content to a file (creates or overwrites).

    Args:
        path: File path (relative to cwd or absolute)
        content: Complete file content
    """
    return ctx.deps.fs.write(path, content)


def read_file(ctx: RunContext[AgentDeps], path: str) -> str:
    """
    Read contents of a file.

    Args:
        path: File path (relative to cwd or absolute)
    """
    return ctx.deps.fs.read(path)


def run_shell(ctx: RunContext[AgentDeps], command: str) -> str:
    """
    Execute a shell command. Use write_file/read_file for file operations.
    Supported: ls, rm, pwd, cd, mkdir, touch, mv, grep, python.
    Note: grep patterns with spaces require regex (e.g., hello\\s+world).
    """
    fs = ctx.deps.fs
    parts = command.split(" ", 1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "ls":
        return fs.list_dir(arg or ".")

    if cmd == "pwd":
        return fs.cwd

    if cmd == "cd":
        fs.cwd = fs._resolve(arg or ".")
        return f"Changed directory to {fs.cwd}"

    if cmd == "rm":
        return fs.delete(arg)

    if cmd == "mkdir":
        if not arg:
            return "Error: mkdir requires a directory path."
        dir_path = fs._resolve(arg)
        marker = f"{dir_path}/.dir"
        if marker not in fs.files:
            fs.files[marker] = ""
        return f"Created directory {dir_path}"

    if cmd == "touch":
        if not arg:
            return "Error: touch requires a file path."
        full_path = fs._resolve(arg)
        if full_path not in fs.files:
            fs.files[full_path] = ""
        return f"Touched {full_path}"

    if cmd == "mv":
        args = arg.split()
        if len(args) != 2:
            return "Error: mv requires source and destination paths."
        src, dst = args
        src_path = fs._resolve(src)
        if src_path not in fs.files:
            return f"Error: Source {src_path} does not exist."
        content = fs.files[src_path]
        dst_path = fs._resolve(dst)
        fs.files[dst_path] = content
        del fs.files[src_path]
        return f"Moved {src_path} to {dst_path}"

    if cmd == "grep":
        import re
        # Parse flags: -A NUM, -B NUM
        tokens = arg.split()
        after_ctx = before_ctx = 0
        while tokens and tokens[0].startswith("-"):
            flag = tokens.pop(0)
            if flag in ("-A", "-B") and tokens:
                try:
                    val = int(tokens.pop(0))
                    if flag == "-A":
                        after_ctx = val
                    else:
                        before_ctx = val
                except ValueError:
                    return f"Error: {flag} requires a number"
            else:
                return f"Error: Unknown flag {flag}. Usage: grep [-A NUM] [-B NUM] PATTERN [PATH]"

        if not tokens:
            return "Usage: grep [-A NUM] [-B NUM] PATTERN [PATH]"
        pattern = tokens[0]
        target = fs._resolve(tokens[1] if len(tokens) > 1 else ".")

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

        results = []
        for filepath, content in fs.files.items():
            if filepath.endswith("/.dir"):
                continue
            if not filepath.startswith(target):
                continue
            if target in fs.files and filepath != target:
                continue

            lines = content.split("\n")
            matched_ranges = set()

            # Find all matching line indices and their context ranges
            for i, line in enumerate(lines):
                if regex.search(line):
                    start = max(0, i - before_ctx)
                    end = min(len(lines), i + after_ctx + 1)
                    for j in range(start, end):
                        matched_ranges.add((j, j == i))

            # Output lines in order, marking matches
            prev_idx = -2
            for idx in sorted(set(j for j, _ in matched_ranges)):
                is_match = any(m for j, m in matched_ranges if j == idx)
                if idx > prev_idx + 1 and prev_idx >= 0:
                    results.append("--")
                marker = ":" if is_match else "-"
                results.append(f"{filepath}:{idx + 1}{marker}{lines[idx]}")
                prev_idx = idx

        if not results:
            return "No matches found."
        if len(results) > 100:
            return f"Found {len(results)} lines (showing first 100):\n" + "\n".join(results[:100])
        return "\n".join(results)

    if cmd == "python":
        workspace = ctx.deps.workspace_path
        if not workspace:
            return "Error: No workspace configured for Python execution."
        fs.save_to_disk(workspace)
        script_path = arg
        if script_path.startswith(VIRTUAL_ROOT + "/"):
            script_path = script_path[len(VIRTUAL_ROOT) + 1:]
        try:
            result = subprocess.run(
                ["python", script_path],
                cwd=workspace,
                capture_output=True,
                timeout=30,
                text=True,
            )
            output = result.stdout + result.stderr
            return output.strip() if output.strip() else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Execution timed out (30s limit)."

    return f"Error: Command '{cmd}' not implemented in virtual sandbox."


# ─────────────────────────────────────────────────────────────
# Tool Registration
# ─────────────────────────────────────────────────────────────

TOOLS = [write_file, read_file, run_shell]

# Load LLMpedia plugin (example of external knowledge base integration)
try:
    from llmpedia import TOOLS as _LLMPEDIA_TOOLS
    TOOLS.extend(_LLMPEDIA_TOOLS)
except ImportError:
    pass

# Load custom user tools
try:
    from custom_tools import TOOLS as _CUSTOM_TOOLS
    TOOLS.extend(_CUSTOM_TOOLS)
except ImportError:
    pass


def create_agent(
    model_key: str = "openai",
    thinking_effort: ThinkingEffort = "high"
) -> Agent[AgentDeps]:
    """Create agent with specified model and thinking effort."""
    return Agent(
        MODELS[model_key],
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        model_settings=_build_settings(model_key, thinking_effort),
        tools=TOOLS,
    )


agent = create_agent()


def _format_args(args: dict | str, max_len: int = 60) -> str:
    if isinstance(args, str):
        args = json.loads(args)
    result = ", ".join(f"{k}={v!r}" for k, v in args.items())
    return result[:max_len] + "..." if len(result) > max_len else result


def _truncate(text: str, max_len: int) -> str:
    text = text.replace("\n", " ").strip()
    return text[:max_len] + "..." if len(text) > max_len else text


async def run_streaming(prompt: str, deps: AgentDeps) -> None:
    """Run agent with streaming output to terminal."""
    tool_calls = 0
    steps = 0

    async for event in agent.run_stream_events(prompt, deps=deps):
        if isinstance(event, PartDeltaEvent):
            if isinstance(event.delta, ThinkingPartDelta) and event.delta.content_delta:
                sys.stdout.write(f"\033[90m{event.delta.content_delta}\033[0m")
                sys.stdout.flush()
        elif isinstance(event, FunctionToolCallEvent):
            tool_calls += 1
            steps += 1
            name = event.part.tool_name
            args = _format_args(event.part.args)
            print(f"\n\033[90m[tool]\033[0m {name}({args})")
        elif isinstance(event, FunctionToolResultEvent):
            result = _truncate(str(event.result.content), 200)
            print(f"\033[90m[result]\033[0m {result}")
        elif hasattr(event, 'result'):
            # Final result
            steps += 1
            print(f"\n{event.result.output}")
            if tool_calls > 0:
                print(f"\n[{steps} steps, {tool_calls} tool calls]")


async def run_blocking(prompt: str, deps: AgentDeps) -> None:
    """Run agent without streaming (for piped output)."""
    result = await agent.run(prompt, deps=deps)
    print(result.output)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python virtual_agent.py <prompt>")
        print("For interactive mode: python tui.py")
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    fs = VirtualFileSystem()
    workspace = Path("./workspace")
    fs.load_from_disk(workspace)
    deps = AgentDeps(fs=fs, user_name="user", workspace_path=workspace)

    if sys.stdout.isatty():
        await run_streaming(prompt, deps)
    else:
        await run_blocking(prompt, deps)


if __name__ == "__main__":
    asyncio.run(main())
