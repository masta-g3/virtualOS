# Research Agent Tools Integration

Expose `research_tools.py` functions to the virtual agent as PydanticAI tools, enabling a complete research workflow within the sandbox.

## Summary

Added three research tools to the virtual agent:
- `search_arxiv` - Search papers with semantic queries and text filters
- `get_paper_summaries` - Get summaries at low/medium/high resolution
- `fetch_paper` - Download full paper markdown to VFS

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Research Workflow                              │
│                                                                         │
│   1. DISCOVER          2. EVALUATE          3. DEEP DIVE               │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│   │search_arxiv  │───►│get_summaries │───►│ fetch_paper  │              │
│   │              │    │              │    │              │              │
│   │ • semantic   │    │ • low res    │    │ • full MD    │              │
│   │ • filters    │    │ • medium     │    │ • to VFS     │              │
│   │ • date range │    │ • high       │    │              │              │
│   └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                 │                        │
│   4. ANALYZE                                    ▼                        │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                   VirtualFileSystem                              │   │
│   │  /home/user/papers/*.md   ← full papers available for reading   │   │
│   │  /home/user/scratchpad.md ← agent accumulates research notes    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Design Decisions

### Two Research Modes

**Narrow/Deep** (1-3 papers): Skip summaries → fetch full papers directly

**Broad/Survey** (5+ papers): Summaries first → triage → escalate selectively

### No Edit Tool

The read+write pattern suffices for scratchpad updates. An edit tool would add complexity without significant benefit for research notes.

### VFS Integration

Papers download into VFS at `/home/user/papers/` (not real disk), maintaining sandbox isolation. `ctrl+s` syncs to disk when persistence is needed.

## Completed

- [x] Import research_tools functions in virtual_agent.py
- [x] Add `search_arxiv` tool wrapper
- [x] Add `get_paper_summaries` tool wrapper
- [x] Add `fetch_paper` tool with VFS integration
- [x] Update system prompt with research workflow documentation
- [x] Update docs/STRUCTURE.md with research workflow
- [x] Fix google-genai API: `contents` parameter, load_dotenv()
