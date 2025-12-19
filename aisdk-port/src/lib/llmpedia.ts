import pg from "pg";
import { GoogleGenerativeAI } from "@google/generative-ai";

const DB_URL =
  process.env.LLMPEDIA_DB_URL ??
  "REDACTED_DB_URL";
const EMBEDDING_MODEL = "text-embedding-004";
const S3_BASE = "https://arxiv-md.s3.amazonaws.com";

const RESOLUTION_TOKENS: Record<string, number> = {
  low: 500,
  medium: 1000,
  high: 2500,
};

let pool: pg.Pool | null = null;
function getPool(): pg.Pool {
  if (!pool) {
    pool = new pg.Pool({ connectionString: DB_URL });
  }
  return pool;
}

async function getEmbedding(text: string): Promise<number[]> {
  const apiKey =
    process.env.GOOGLE_API_KEY ?? process.env.GOOGLE_GENERATIVE_AI_API_KEY;
  if (!apiKey) throw new Error("GOOGLE_API_KEY not set");
  const ai = new GoogleGenerativeAI(apiKey);
  const model = ai.getGenerativeModel({ model: EMBEDDING_MODEL });
  const result = await model.embedContent(text);
  return result.embedding.values;
}

export interface Paper {
  arxiv_code: string;
  title: string;
  authors: string;
  published: string | null;
  abstract: string | null;
  similarity?: number;
}

export interface SearchParams {
  query?: string;
  title_contains?: string;
  abstract_contains?: string;
  author?: string;
  published_after?: string;
  published_before?: string;
  similarity_threshold?: number;
  limit?: number;
}

export async function searchPapers(params: SearchParams): Promise<Paper[]> {
  const pool = getPool();
  const {
    query,
    title_contains,
    abstract_contains,
    author,
    published_after,
    published_before,
    similarity_threshold = 0.5,
    limit = 20,
  } = params;

  const conditions: string[] = [];
  const values: unknown[] = [];
  let paramIndex = 1;

  let baseQuery: string;
  if (query) {
    const embedding = await getEmbedding(query);
    baseQuery = `
      SELECT d.arxiv_code, d.title, d.authors, d.published, d.summary,
             1 - (e.embedding <=> $${paramIndex}::vector) as similarity
      FROM arxiv_details d
      JOIN arxiv_embeddings_3072 e ON d.arxiv_code = e.arxiv_code
      WHERE e.doc_type = 'template' AND e.embedding_type = 'gemini'
        AND 1 - (e.embedding <=> $${paramIndex}::vector) >= $${paramIndex + 1}
    `;
    values.push(`[${embedding.join(",")}]`, similarity_threshold);
    paramIndex += 2;
  } else {
    baseQuery = `
      SELECT d.arxiv_code, d.title, d.authors, d.published, d.summary,
             NULL as similarity
      FROM arxiv_details d
      WHERE 1=1
    `;
  }

  if (title_contains) {
    conditions.push(`d.title ILIKE $${paramIndex++}`);
    values.push(`%${title_contains}%`);
  }
  if (abstract_contains) {
    conditions.push(`d.summary ILIKE $${paramIndex++}`);
    values.push(`%${abstract_contains}%`);
  }
  if (author) {
    conditions.push(`d.authors ILIKE $${paramIndex++}`);
    values.push(`%${author}%`);
  }
  if (published_after) {
    conditions.push(`d.published >= $${paramIndex++}`);
    values.push(published_after);
  }
  if (published_before) {
    conditions.push(`d.published <= $${paramIndex++}`);
    values.push(published_before);
  }

  let sql = baseQuery;
  if (conditions.length) {
    sql += " AND " + conditions.join(" AND ");
  }
  sql += query ? " ORDER BY similarity DESC" : " ORDER BY d.published DESC";
  sql += ` LIMIT $${paramIndex}`;
  values.push(limit);

  const result = await pool.query(sql, values);
  return result.rows.map((row) => ({
    arxiv_code: row.arxiv_code,
    title: row.title,
    authors: row.authors,
    published: row.published?.toISOString().split("T")[0] ?? null,
    abstract: row.summary?.slice(0, 500) ?? null,
    ...(row.similarity != null && {
      similarity: Math.round(row.similarity * 1000) / 1000,
    }),
  }));
}

export async function getSummaries(
  arxiv_codes: string[],
  resolution: "low" | "medium" | "high" = "medium"
): Promise<Record<string, string>> {
  if (arxiv_codes.length === 0) return {};

  const pool = getPool();
  const targetTokens = RESOLUTION_TOKENS[resolution];

  const result = await pool.query(
    `SELECT DISTINCT ON (arxiv_code) arxiv_code, summary
     FROM summary_notes
     WHERE arxiv_code = ANY($1)
     ORDER BY arxiv_code, ABS(tokens - $2)`,
    [arxiv_codes, targetTokens]
  );

  return Object.fromEntries(result.rows.map((r) => [r.arxiv_code, r.summary]));
}

export async function fetchPaperMarkdown(
  arxiv_code: string
): Promise<string | null> {
  const url = `${S3_BASE}/${arxiv_code}/paper.md`;
  const response = await fetch(url);
  if (!response.ok) return null;
  return response.text();
}
