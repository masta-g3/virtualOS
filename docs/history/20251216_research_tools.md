# Research Tools

Tools for querying the LLMpedia PostgreSQL database to research arXiv papers.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     research_tools.py                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  search_papers()     ──────►  arxiv_details + embeddings_3072   │
│  get_summaries()     ──────►  summary_notes                     │
│  download_paper()    ──────►  S3 (arxiv-md bucket)              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## API

### `search_papers()`

Search papers with text filters and optional semantic search.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | str \| None | Semantic search (requires GOOGLE_API_KEY) |
| `title_contains` | str \| None | Substring match in title |
| `abstract_contains` | str \| None | Substring match in abstract |
| `author` | str \| None | Author name substring |
| `published_after` | str \| None | ISO date "2024-01-01" |
| `published_before` | str \| None | ISO date |
| `similarity_threshold` | float | Min similarity 0-1 (default 0.5) |
| `limit` | int | Max results (default 20) |

### `get_summaries()`

Retrieve summaries at configurable detail levels.

| Parameter | Type | Description |
|-----------|------|-------------|
| `arxiv_codes` | list[str] | Paper codes |
| `resolution` | str | "low" (~500 tokens), "medium" (~1000), "high" (~2500) |

### `download_paper()` / `download_papers()`

Download full paper markdown from S3 to `workspace/papers/`.

## Completed

- [x] Dependencies: psycopg2-binary, google-genai, requests
- [x] Text-based search with ILIKE filters
- [x] Token-based resolution mapping for summaries
- [x] Single and batch paper download
- [x] Semantic search via Gemini embeddings (requires GOOGLE_API_KEY)
