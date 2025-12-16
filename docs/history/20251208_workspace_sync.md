# agent-006: Workspace Sync

Bidirectional sync between a host folder (`./workspace/`) and the VirtualFileSystem.

## Problem

Currently, VirtualFileSystem starts empty (except for a demo `readme.txt`). Users can't:
1. Load existing files to work with
2. Save agent-created files back to disk

## UX Design

**Principle:** Invisible when not needed, obvious when it matters.

### Sync Model: Explicit Save

After considering auto-sync, file watching, and other approaches, **explicit save** wins for simplicity:

| Approach | Pros | Cons |
|----------|------|------|
| Auto-sync on every write | Always in sync | Noisy, unexpected disk writes |
| File watcher (live reload) | Real-time | Complex, race conditions, overkill |
| **Explicit save (ctrl+s)** | User controls when | Must remember to save |
| Save on quit | Simple | Risk of losing work on crash |

**Decision:** `ctrl+s` to sync, with unsaved indicator in header.

### User Flow

```
1. User places files in ./workspace/
2. User runs: uv run python tui.py
3. TUI loads workspace/* into /home/user/*
4. Agent reads/writes files in virtual filesystem
5. User presses ctrl+s → changes written back to ./workspace/
6. Header shows sync status: "Virtual OS" vs "Virtual OS [modified]"
```

### Visual Feedback

```
┌─────────────────────────────────────────────────────────────┐
│ Virtual OS [modified]                          ctrl+s: save │
├─────────────────────────────────────────────────────────────┤
│ > create a hello.py that prints hello world                 │
│   [run_shell] {"command":"echo \"print('hello')\" > hello.py"}│
│ Done! Created hello.py                                      │
│                                                             │
│ > save my changes                                           │
│ [Workspace saved to ./workspace/]                           │
└─────────────────────────────────────────────────────────────┘
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         tui.py                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ VirtualAgentApp                                     │    │
│  │  - workspace_path: Path                             │    │
│  │  - modified: bool                                   │    │
│  │  - action_save() → sync to disk                     │    │
│  └─────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │ uses
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    virtual_agent.py                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ VirtualFileSystem                                   │    │
│  │  + load_from_disk(path) → populate files dict       │    │
│  │  + save_to_disk(path) → write files dict to disk    │    │
│  │  + get_modified_files(snapshot) → changed files     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Startup:
  ./workspace/*.py  ──load_from_disk()──►  fs.files["/home/user/*.py"]

Runtime:
  Agent writes  ──►  fs.files modified  ──►  modified = True

Save (ctrl+s):
  fs.files  ──save_to_disk()──►  ./workspace/*  ──►  modified = False
```

## Implementation Details

### 1. VirtualFileSystem Extensions (`virtual_agent.py`)

Add two methods to VirtualFileSystem:

```python
from pathlib import Path

@dataclass
class VirtualFileSystem:
    files: dict[str, str] = field(default_factory=dict)
    cwd: str = "/home/user"

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
                    pass  # skip binary/unreadable files
        return count

    def save_to_disk(self, host_path: Path, virtual_root: str = "/home/user") -> int:
        """Save virtual files back to host folder. Returns count."""
        count = 0
        host_path.mkdir(parents=True, exist_ok=True)
        for virtual_path, content in self.files.items():
            if virtual_path.startswith(virtual_root):
                relative = virtual_path[len(virtual_root):].lstrip("/")
                if relative:  # skip root itself
                    target = host_path / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)
                    count += 1
        return count
```

### 2. TUI Changes (`tui.py`)

```python
from pathlib import Path

WORKSPACE_PATH = Path("./workspace")

class VirtualAgentApp(App):
    CSS_PATH = "tui.tcss"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+s", "save", "Save"),  # NEW
    ]

    def __init__(self):
        super().__init__()
        self.fs = VirtualFileSystem()
        self.workspace_path = WORKSPACE_PATH
        self.modified = False
        self._initial_snapshot: dict[str, str] = {}

        # Load workspace
        count = self.fs.load_from_disk(self.workspace_path)
        if count == 0:
            self.fs.files["/home/user/readme.txt"] = "Welcome to Virtual OS."

        # Snapshot for change detection
        self._initial_snapshot = dict(self.fs.files)

        self.deps = AgentDeps(fs=self.fs, user_name="user")
        self.history: list[ModelMessage] = []

    def compose(self) -> ComposeResult:
        yield Static("Virtual OS", id="header")
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="prompt")

    def _update_header(self) -> None:
        """Update header to show modified status."""
        header = self.query_one("#header", Static)
        if self.modified:
            header.update("Virtual OS [modified]")
        else:
            header.update("Virtual OS")

    def _check_modified(self) -> None:
        """Check if filesystem differs from snapshot."""
        self.modified = self.fs.files != self._initial_snapshot
        self._update_header()

    async def _run_agent(self, ...):
        # ... existing code ...
        self._check_modified()  # ADD after agent completes

    async def action_save(self) -> None:
        """Save workspace to disk."""
        count = self.fs.save_to_disk(self.workspace_path)
        self._initial_snapshot = dict(self.fs.files)
        self.modified = False
        self._update_header()

        # Show confirmation in messages
        messages = self.query_one("#messages", VerticalScroll)
        confirm = Static(f"[Saved {count} files to {self.workspace_path}/]", classes="system-message")
        await messages.mount(confirm)
        messages.scroll_end()
```

### 3. Style Addition (`tui.tcss`)

```tcss
.system-message {
    color: #22c55e;
    text-style: italic;
    margin: 0 0 1 0;
}
```

### 4. Workspace Folder

Create `./workspace/.gitkeep` so the folder exists but is empty by default.

## Edge Cases

| Case | Behavior |
|------|----------|
| `./workspace/` doesn't exist | Create on first save |
| Binary file in workspace | Skip silently on load |
| File deleted in VFS | Not deleted on disk (safe default) |
| No changes made | ctrl+s still works, saves same content |
| Large files (>1MB) | Load anyway (revisit if problematic) |
| Nested directories | Supported via `rglob` and `mkdir(parents=True)` |

## Implementation Phases

### Phase 1: Core Sync
- [x] Add `load_from_disk()` to VirtualFileSystem
- [x] Add `save_to_disk()` to VirtualFileSystem
- [x] Test both methods in isolation

### Phase 2: TUI Integration
- [x] Add workspace loading on TUI startup
- [x] Add `ctrl+s` binding and `action_save()`
- [x] Add modified state tracking
- [x] Update header to show modified status
- [x] Add system message style

### Phase 3: Polish
- [x] Create `./workspace/.gitkeep`
- [x] Test full flow: load → modify → save
- [x] Update docs/STRUCTURE.md with workspace info

## Testing Checklist

1. [x] Empty workspace → TUI shows readme.txt
2. [x] Files in workspace → TUI loads them (verify with `ls`)
3. [x] Agent creates file → header shows [modified]
4. [x] ctrl+s → file appears in ./workspace/
5. [x] Nested files work (workspace/sub/file.py)
6. [x] Binary files skipped without error

## Out of Scope

- File deletion sync (too dangerous)
- Auto-save / file watching
- CLI args for custom workspace path
- Conflict resolution
- `.gitignore` support
