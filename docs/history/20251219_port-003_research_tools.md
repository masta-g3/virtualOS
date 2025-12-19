# port-003: Research Tools for AI SDK Agent

Add research tools (search, summaries, fetch) to the TypeScript AI SDK agent, porting functionality from `research_tools.py`.

## Summary

Implemented three research tools for the AI SDK port:
- `searchArxiv` - Semantic/text search against LLMpedia PostgreSQL
- `getPaperSummaries` - Retrieve summaries at low/medium/high detail levels
- `fetchPaper` - Download full paper markdown from S3 to VFS

## Architecture

```
aisdk-port/src/
├── agent.ts              # Imports and registers research tools
├── tools/
│   ├── file-tools.ts     # Existing
│   └── research-tools.ts # search, summaries, fetch
└── lib/
    └── llmpedia.ts       # Database + embedding client
```

### Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Agent Call    │────▶│  research-tools  │────▶│   llmpedia.ts   │
│ (search_arxiv)  │     │  (AI SDK tools)  │     │  (DB + embed)   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────────┐
                        ▼                                 ▼                 ▼
                ┌───────────────┐              ┌─────────────────┐  ┌──────────────┐
                │ Google Gemini │              │ PostgreSQL      │  │ S3 (arxiv-md)│
                │ (embeddings)  │              │ (LLMpedia DB)   │  │ paper.md     │
                └───────────────┘              └─────────────────┘  └──────────────┘
```

## Dependencies

- `pg` - PostgreSQL client
- `@google/generative-ai` - Gemini embeddings
- `@types/pg` - TypeScript types

Environment variables:
- `LLMPEDIA_DB_URL` - PostgreSQL connection string
- `GOOGLE_API_KEY` or `GOOGLE_GENERATIVE_AI_API_KEY` - Gemini API key

## Completed

- [x] Install dependencies
- [x] Create `src/lib/llmpedia.ts` with connection pool and embedding function
- [x] Implement `searchPapers()`, `getSummaries()`, `fetchPaperMarkdown()`
- [x] Create `src/tools/research-tools.ts` with AI SDK tool definitions
- [x] Integrate into `agent.ts`
- [x] TypeScript type-checking passes
