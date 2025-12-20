import { describe, it, expect, vi, beforeEach } from "vitest";

const mockQuery = vi.fn();
vi.mock("pg", () => ({
  default: {
    Pool: vi.fn(() => ({ query: mockQuery })),
  },
}));

vi.mock("@google/generative-ai", () => ({
  GoogleGenerativeAI: vi.fn(() => ({
    getGenerativeModel: vi.fn(() => ({
      embedContent: vi.fn(() =>
        Promise.resolve({ embedding: { values: [0.1, 0.2, 0.3] } })
      ),
    })),
  })),
}));

process.env.GOOGLE_API_KEY = "test-key";

import { searchPapers, getSummaries, fetchPaperMarkdown } from "../src/lib/llmpedia.js";

describe("llmpedia", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("searchPapers", () => {
    it("builds semantic query with embedding when query provided", async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await searchPapers({ query: "attention mechanism", limit: 5 });

      expect(mockQuery).toHaveBeenCalledTimes(1);
      const [sql, values] = mockQuery.mock.calls[0];

      expect(sql).toContain("embedding <=>");
      expect(sql).toContain("similarity");
      expect(sql).toContain("ORDER BY similarity DESC");
      expect(values[0]).toBe("[0.1,0.2,0.3]");
      expect(values[1]).toBe(0.5); // default threshold
      expect(values[2]).toBe(5);
    });

    it("builds filter-only query when no semantic query", async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await searchPapers({ title_contains: "transformer", limit: 10 });

      const [sql, values] = mockQuery.mock.calls[0];

      expect(sql).not.toContain("embedding <=>");
      expect(sql).toContain("title ILIKE");
      expect(sql).toContain("ORDER BY d.published DESC");
      expect(values[0]).toBe("%transformer%");
    });

    it("combines multiple filters correctly", async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await searchPapers({
        title_contains: "attention",
        author: "Vaswani",
        published_after: "2020-01-01",
        published_before: "2024-01-01",
        limit: 20,
      });

      const [sql, values] = mockQuery.mock.calls[0];

      expect(sql).toContain("title ILIKE");
      expect(sql).toContain("authors ILIKE");
      expect(sql).toContain("published >=");
      expect(sql).toContain("published <=");
      expect(values).toContain("%attention%");
      expect(values).toContain("%Vaswani%");
      expect(values).toContain("2020-01-01");
      expect(values).toContain("2024-01-01");
    });

    it("transforms row data to Paper format", async () => {
      mockQuery.mockResolvedValue({
        rows: [
          {
            arxiv_code: "2401.12345",
            title: "Test Paper",
            authors: "Test Author",
            published: new Date("2024-01-15"),
            summary: "This is a very long abstract that will be truncated...",
            similarity: 0.8765,
          },
        ],
      });

      const papers = await searchPapers({ query: "test" });

      expect(papers[0]).toEqual({
        arxiv_code: "2401.12345",
        title: "Test Paper",
        authors: "Test Author",
        published: "2024-01-15",
        abstract: expect.any(String),
        similarity: 0.877, // rounded
      });
    });
  });

  describe("getSummaries", () => {
    it("queries for summaries at target resolution", async () => {
      mockQuery.mockResolvedValue({
        rows: [
          { arxiv_code: "2401.12345", summary: "Summary text" },
        ],
      });

      const result = await getSummaries(["2401.12345"], "medium");

      const [sql, values] = mockQuery.mock.calls[0];
      expect(sql).toContain("summary_notes");
      expect(sql).toContain("ABS(tokens - $2)");
      expect(values[0]).toEqual(["2401.12345"]);
      expect(values[1]).toBe(1000); // medium = 1000 tokens
      expect(result).toEqual({ "2401.12345": "Summary text" });
    });

    it("returns empty object for empty input", async () => {
      const result = await getSummaries([], "low");
      expect(mockQuery).not.toHaveBeenCalled();
      expect(result).toEqual({});
    });

    it("uses correct token counts for resolutions", async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await getSummaries(["test"], "low");
      expect(mockQuery.mock.calls[0][1][1]).toBe(500);

      await getSummaries(["test"], "high");
      expect(mockQuery.mock.calls[1][1][1]).toBe(2500);
    });
  });

  describe("fetchPaperMarkdown", () => {
    it("fetches from S3 URL", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        text: () => Promise.resolve("# Paper Content"),
      });
      global.fetch = mockFetch;

      const result = await fetchPaperMarkdown("2401.12345");

      expect(mockFetch).toHaveBeenCalledWith(
        "https://arxiv-md.s3.amazonaws.com/2401.12345/paper.md"
      );
      expect(result).toBe("# Paper Content");
    });

    it("returns null on 404", async () => {
      global.fetch = vi.fn().mockResolvedValue({ ok: false });

      const result = await fetchPaperMarkdown("nonexistent");
      expect(result).toBeNull();
    });
  });
});
