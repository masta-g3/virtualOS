import asyncio
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

load_dotenv()


@dataclass
class VirtualFileSystem:
    """In-memory filesystem. Data is lost when the script ends."""

    files: dict[str, str] = field(default_factory=dict)
    cwd: str = "/home/user"

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

    def load_from_disk(self, host_path: Path, virtual_root: str = "/home/user") -> int:
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

    def save_to_disk(self, host_path: Path, virtual_root: str = "/home/user") -> int:
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


agent = Agent(
    "openai-responses:gpt-5.1-codex-mini",
    deps_type=AgentDeps,
    system_prompt=(
        "You are a coding assistant in a Virtual Terminal. "
        "You can manipulate files and run simulated bash commands in your virtual filesystem. "
        "Available commands: ls, cat (read only), echo (with > to write files), rm, pwd, cd, python. "
        "No heredoc syntax - use echo with \\n for multiline content. "
        "When asked to write code, save it to a file first."
    ),
    model_settings=OpenAIResponsesModelSettings(
        openai_reasoning_effort="high",
        openai_reasoning_summary="detailed",
    ),
)


@agent.tool
def run_shell(ctx: RunContext[AgentDeps], command: str) -> str:
    """
    Execute a simulated shell command.
    Supported: ls, cat, echo, rm, pwd, cd, python.

    Examples:
    - ls
    - cat myfile.py
    - echo "print('hello')" > hello.py
    - rm oldfile.txt
    - python script.py
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
        if arg.startswith("/"):
            fs.cwd = arg
        else:
            fs.cwd = f"{fs.cwd.rstrip('/')}/{arg}"
        return f"Changed directory to {fs.cwd}"

    if cmd == "cat":
        return fs.read(arg)

    if cmd == "rm":
        return fs.delete(arg)

    if cmd == "echo":
        if ">" in arg:
            content_part, file_part = arg.rsplit(">", 1)
            content = content_part.strip().strip('"').strip("'")
            content = content.replace("\\n", "\n").replace("\\t", "\t")
            filename = file_part.strip()
            return fs.write(filename, content)
        return arg

    if cmd == "python":
        workspace = ctx.deps.workspace_path
        if not workspace:
            return "Error: No workspace configured for Python execution."
        fs.save_to_disk(workspace)
        script_path = arg
        if script_path.startswith("/home/user/"):
            script_path = script_path[len("/home/user/"):]
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


async def main():
    print("--- Initializing Virtual OS ---")
    virtual_fs = VirtualFileSystem()
    virtual_fs.files["/home/user/readme.txt"] = "Welcome to the Matrix."

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
