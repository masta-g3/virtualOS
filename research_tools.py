"""
Research tools for querying LLMpedia PostgreSQL database.

Environment variables:
    LLMPEDIA_DB_URL: PostgreSQL connection string
    GOOGLE_API_KEY: For Gemini embeddings (semantic search)
"""

import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import psycopg2
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

DB_URL = os.getenv(
    "LLMPEDIA_DB_URL",
    "REDACTED_DB_URL"
)
EMBEDDING_MODEL = "gemini-embedding-001"
S3_BASE = "https://arxiv-md.s3.amazonaws.com"

RESOLUTION_TOKENS = {
    "low": 500,
    "medium": 1000,
    "high": 2500,
}


def _get_connection():
    return psycopg2.connect(DB_URL)


def _get_embedding(text: str) -> list[float]:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
    client = genai.Client(api_key=api_key)
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )
    return response.embeddings[0].values


def search_papers(
    query: str | None = None,
    title_contains: str | None = None,
    abstract_contains: str | None = None,
    author: str | None = None,
    published_after: str | None = None,
    published_before: str | None = None,
    similarity_threshold: float = 0.5,
    limit: int = 20
) -> list[dict]:
    """
    Search papers with filters and optional semantic search.

    Args:
        query: Semantic search query (uses embeddings)
        title_contains: Substring match in title
        abstract_contains: Substring match in abstract
        author: Author name substring
        published_after: ISO date string "2024-01-01"
        published_before: ISO date string
        similarity_threshold: Minimum similarity for semantic search (0-1)
        limit: Max results

    Returns:
        List of paper dicts with arxiv_code, title, authors, published, abstract.
        If semantic search, includes similarity score.
    """
    conn = _get_connection()
    cur = conn.cursor()

    conditions = []
    params = []

    if query:
        embedding = _get_embedding(query)
        base_query = """
            SELECT d.arxiv_code, d.title, d.authors, d.published, d.summary,
                   1 - (e.embedding <=> %s::vector) as similarity
            FROM arxiv_details d
            JOIN arxiv_embeddings_3072 e ON d.arxiv_code = e.arxiv_code
            WHERE e.doc_type = 'template' AND e.embedding_type = 'gemini'
              AND 1 - (e.embedding <=> %s::vector) >= %s
        """
        params = [embedding, embedding, similarity_threshold]
    else:
        base_query = """
            SELECT d.arxiv_code, d.title, d.authors, d.published, d.summary,
                   NULL as similarity
            FROM arxiv_details d
            WHERE 1=1
        """

    if title_contains:
        conditions.append("d.title ILIKE %s")
        params.append(f"%{title_contains}%")

    if abstract_contains:
        conditions.append("d.summary ILIKE %s")
        params.append(f"%{abstract_contains}%")

    if author:
        conditions.append("d.authors ILIKE %s")
        params.append(f"%{author}%")

    if published_after:
        conditions.append("d.published >= %s")
        params.append(published_after)

    if published_before:
        conditions.append("d.published <= %s")
        params.append(published_before)

    sql = base_query
    if conditions:
        sql += " AND " + " AND ".join(conditions)

    if query:
        sql += " ORDER BY similarity DESC"
    else:
        sql += " ORDER BY d.published DESC"

    sql += " LIMIT %s"
    params.append(limit)

    cur.execute(sql, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    results = []
    for row in rows:
        paper = {
            "arxiv_code": row[0],
            "title": row[1],
            "authors": row[2],
            "published": row[3].strftime("%Y-%m-%d") if row[3] else None,
            "abstract": row[4][:500] if row[4] else None,
        }
        if row[5] is not None:
            paper["similarity"] = round(row[5], 3)
        results.append(paper)

    return results


def get_summaries(
    arxiv_codes: list[str],
    resolution: str = "medium"
) -> dict[str, str]:
    """
    Get paper summaries at specified resolution.

    Args:
        arxiv_codes: List of arxiv codes
        resolution: "low" (~500 tokens), "medium" (~1000), "high" (~2500)

    Returns:
        Dict mapping arxiv_code to summary text.
    """
    if not arxiv_codes:
        return {}

    target_tokens = RESOLUTION_TOKENS.get(resolution, 1000)

    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT ON (arxiv_code) arxiv_code, summary, tokens
        FROM summary_notes
        WHERE arxiv_code = ANY(%s)
        ORDER BY arxiv_code, ABS(tokens - %s)
    """, (arxiv_codes, target_tokens))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {row[0]: row[1] for row in rows}


def download_paper(
    arxiv_code: str,
    output_dir: str = "workspace/papers"
) -> str | None:
    """
    Download paper markdown from S3.

    Args:
        arxiv_code: ArXiv paper code
        output_dir: Directory to save markdown

    Returns:
        Local file path on success, None on failure.
    """
    url = f"{S3_BASE}/{arxiv_code}/paper.md"
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        return None

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filepath = Path(output_dir) / f"{arxiv_code}.md"
    filepath.write_text(response.text)
    return str(filepath)


def download_papers(
    arxiv_codes: list[str],
    output_dir: str = "workspace/papers",
    max_workers: int = 5
) -> dict[str, str | None]:
    """
    Download multiple papers in parallel.

    Args:
        arxiv_codes: List of arxiv codes
        output_dir: Directory to save markdowns
        max_workers: Thread pool size

    Returns:
        Dict mapping arxiv_code to filepath or None.
    """
    def _download(code: str) -> tuple[str, str | None]:
        return (code, download_paper(code, output_dir))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_download, arxiv_codes))

    return dict(results)
