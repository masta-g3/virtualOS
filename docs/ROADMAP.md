# Roadmap

Track what's planned, what's done, and what's explicitly out of scope.

## Implemented

### Agent (`virtual_agent.py`)
- [x] VirtualFileSystem - in-memory dict-based filesystem
- [x] run_shell tool - ls, cat, echo, rm, pwd, cd
- [x] AgentDeps for dependency injection
- [x] Workspace sync - load from `./workspace/`, save with ctrl+s
- [x] Python execution - `python script.py` runs in workspace

### TUI (`tui.py`)
- [x] Input prompt with conversation loop
- [x] Tool calls displayed inline (blue, italic)
- [x] Markdown rendering for responses
- [x] Message history across turns
- [x] Clear messages (ctrl+l)
- [x] Error display (red)
- [x] Modified indicator in header

## Wishlist

Ideas under consideration. Must justify value before implementing.

### Agent
- [ ] mkdir, touch, mv commands
- [ ] File content search (grep-like)
- [ ] Multi-file operations

### TUI
- [ ] Loading indicator during agent work
- [ ] Syntax highlighting in code blocks
- [ ] Session persistence (save/restore history)
- [ ] Scrollable tool call output (collapse long results)

## Out of Scope

**Do not implement** unless fundamentally rethinking the project:

- Multi-agent support - adds complexity, no clear use case
- Real filesystem access - defeats sandbox purpose
- Custom themes/configuration - unnecessary personalization
- Plugin system - premature abstraction
- Network/HTTP tools - scope creep
- Database integration - out of domain
- Authentication/users - not needed for local tool

---

*Before adding a feature: Is it essential? Does it belong in wishlist first? If neither, it doesn't belong here.*
