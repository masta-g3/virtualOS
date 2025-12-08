import asyncio
from dataclasses import dataclass, field

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext

load_dotenv()


@dataclass
class VirtualFileSystem:
    """In-memory filesystem. Data is lost when the script ends."""

    files: dict[str, str] = field(default_factory=dict)
    cwd: str = "/home/user"

    def _resolve(self, path: str) -> str:
        if path.startswith("/"):
            return path
        return f"{self.cwd.rstrip('/')}/{path}"

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


@dataclass
class AgentDeps:
    fs: VirtualFileSystem
    user_name: str


agent = Agent(
    "openai:gpt-4.1-mini",
    deps_type=AgentDeps,
    system_prompt=(
        "You are a coding assistant in a Virtual Terminal. "
        "You can manipulate files and run simulated bash commands in your virtual filesystem. "
        "When asked to write code, save it to a file first. "
        "Use the 'run_shell' tool for file operations."
    ),
)


@agent.tool
def run_shell(ctx: RunContext[AgentDeps], command: str) -> str:
    """
    Execute a simulated shell command.
    Supported: ls, cat, echo, rm, pwd, cd.

    Examples:
    - ls
    - cat myfile.py
    - echo "print('hello')" > hello.py
    - rm oldfile.txt
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
            filename = file_part.strip()
            return fs.write(filename, content)
        return arg

    return f"Error: Command '{cmd}' not implemented in virtual sandbox."


async def main():
    print("--- Initializing Virtual OS ---")
    virtual_fs = VirtualFileSystem()
    virtual_fs.files["/home/user/readme.txt"] = "Welcome to the Matrix."

    deps = AgentDeps(fs=virtual_fs, user_name="Neo")

    prompt = "Create a python script that calculates factorial, save it as math_tools.py, then cat it to verify."
    print(f"User: {prompt}")

    result = await agent.run(prompt, deps=deps)

    print("\n--- Agent Response ---")
    print(result.output)

    print("\n--- Virtual Filesystem State ---")
    for path, content in virtual_fs.files.items():
        print(f"[{path}]:\n{content}\n")


if __name__ == "__main__":
    asyncio.run(main())
