import asyncio
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import requests
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from research_tools import search_papers, get_summaries, S3_BASE

load_dotenv()

VIRTUAL_ROOT = "/home/user"


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
- read_file to get current state
- Append new findings
- write_file to save updates
"""

agent = Agent(
    "openai-responses:gpt-5.1-codex-mini",
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
    model_settings=OpenAIResponsesModelSettings(
        openai_reasoning_effort="high",
        openai_reasoning_summary="detailed",
    ),
)


@agent.tool
def write_file(ctx: RunContext[AgentDeps], path: str, content: str) -> str:
    """
    Write content to a file (creates or overwrites).

    Args:
        path: File path (relative to cwd or absolute)
        content: Complete file content
    """
    return ctx.deps.fs.write(path, content)


@agent.tool
def read_file(ctx: RunContext[AgentDeps], path: str) -> str:
    """
    Read contents of a file.

    Args:
        path: File path (relative to cwd or absolute)
    """
    return ctx.deps.fs.read(path)


@agent.tool
def run_shell(ctx: RunContext[AgentDeps], command: str) -> str:
    """
    Execute a shell command. Use write_file/read_file for file operations.
    Supported: ls, rm, pwd, cd, python.
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


@agent.tool
def search_arxiv(
    ctx: RunContext[AgentDeps],
    query: str | None = None,
    title_contains: str | None = None,
    abstract_contains: str | None = None,
    author: str | None = None,
    published_after: str | None = None,
    published_before: str | None = None,
    limit: int = 10
) -> str:
    """
    Search arXiv papers in LLMpedia database.

    Args:
        query: Semantic search query (finds conceptually similar papers)
        title_contains: Substring to match in paper titles
        abstract_contains: Substring to match in abstracts
        author: Author name to filter by
        published_after: Filter papers after this date (YYYY-MM-DD)
        published_before: Filter papers before this date (YYYY-MM-DD)
        limit: Maximum results (default 10, max 50)
    """
    limit = min(limit, 50)
    results = search_papers(
        query=query,
        title_contains=title_contains,
        abstract_contains=abstract_contains,
        author=author,
        published_after=published_after,
        published_before=published_before,
        limit=limit
    )

    if not results:
        return "No papers found matching criteria."

    lines = [f"Found {len(results)} papers:\n"]
    for paper in results:
        lines.append(f"[{paper['arxiv_code']}] {paper['title']} ({paper['published']})")
        lines.append(f"  Authors: {paper['authors'][:80]}...")
        if paper.get('similarity'):
            lines.append(f"  Similarity: {paper['similarity']}")
        if paper.get('abstract'):
            lines.append(f"  Abstract: {paper['abstract'][:200]}...")
        lines.append("")

    return "\n".join(lines)


@agent.tool
def get_paper_summaries(
    ctx: RunContext[AgentDeps],
    arxiv_codes: list[str],
    resolution: str = "medium"
) -> str:
    """
    Get summaries for papers at specified detail level.

    Args:
        arxiv_codes: List of arXiv paper codes (e.g., ["2401.12345"])
        resolution: Detail level - "low" (~500 tokens), "medium" (~1000), "high" (~2500)
    """
    if not arxiv_codes:
        return "Error: No arxiv codes provided."

    summaries = get_summaries(arxiv_codes, resolution)

    if not summaries:
        return "No summaries found for the provided arxiv codes."

    lines = []
    for code, summary in summaries.items():
        lines.append(f"## {code}\n")
        lines.append(summary)
        lines.append("\n---\n")

    return "\n".join(lines)


@agent.tool
def fetch_paper(ctx: RunContext[AgentDeps], arxiv_code: str) -> str:
    """
    Download full paper markdown into the virtual filesystem.

    The paper will be saved to /home/user/papers/{arxiv_code}.md and can be
    read using the read_file tool.

    Args:
        arxiv_code: The arXiv paper code (e.g., "2401.12345")
    """
    url = f"{S3_BASE}/{arxiv_code}/paper.md"
    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        return f"Error: Could not download paper {arxiv_code} (HTTP {response.status_code})"

    content = response.text
    path = f"{VIRTUAL_ROOT}/papers/{arxiv_code}.md"
    ctx.deps.fs.write(path, content)

    return f"Downloaded {arxiv_code} to {path} ({len(content):,} chars)"


async def main():
    print("--- Initializing Virtual OS ---")
    virtual_fs = VirtualFileSystem()
    virtual_fs.files[f"{VIRTUAL_ROOT}/readme.txt"] = "Welcome to the Matrix."

    deps = AgentDeps(fs=virtual_fs, user_name="Neo")

    prompt = "Create a python script that calculates factorial, save it as math_tools.py, then cat it to verify."
    print(f"User: {prompt}")

    result = await agent.run(prompt, deps=deps, usage_limits=UsageLimits(request_limit=None))

    print("\n--- Agent Response ---")
    print(result.output)

    print("\n--- Virtual Filesystem State ---")
    for path, content in virtual_fs.files.items():
        print(f"[{path}]:\n{content}\n")


if __name__ == "__main__":
    asyncio.run(main())
