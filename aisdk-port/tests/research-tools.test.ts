import { describe, it, expect, vi, beforeEach } from "vitest";
import { VirtualFileSystem } from "../src/virtual-fs.js";
import { createResearchTools } from "../src/tools/research-tools.js";

vi.mock("../src/lib/llmpedia.js", () => ({
  searchPapers: vi.fn(),
  getSummaries: vi.fn(),
  fetchPaperMarkdown: vi.fn(),
}));

import {
  searchPapers,
  getSummaries,
  fetchPaperMarkdown,
} from "../src/lib/llmpedia.js";

const mockSearchPapers = vi.mocked(searchPapers);
const mockGetSummaries = vi.mocked(getSummaries);
const mockFetchPaperMarkdown = vi.mocked(fetchPaperMarkdown);

describe("research tools", () => {
  let fs: VirtualFileSystem;
  let tools: ReturnType<typeof createResearchTools>;
  const execOpts = { toolCallId: "1", messages: [] };

  beforeEach(() => {
    vi.clearAllMocks();
    fs = new VirtualFileSystem();
    tools = createResearchTools(fs);
  });

  describe("searchArxiv", () => {
    it("formats paper results with similarity scores", async () => {
      mockSearchPapers.mockResolvedValue([
        {
          arxiv_code: "2401.12345",
          title: "Attention Is All You Need",
          authors: "Vaswani et al.",
          published: "2017-06-12",
          abstract: "The dominant sequence transduction models...",
          similarity: 0.95,
        },
      ]);

      const result = await tools.searchArxiv.execute(
        { query: "attention mechanism", limit: 10 },
        execOpts
      );

      expect(result).toContain("[2401.12345]");
      expect(result).toContain("Attention Is All You Need");
      expect(result).toContain("Vaswani et al.");
      expect(result).toContain("2017-06-12");
      expect(result).toContain("sim: 0.95");
    });

    it("returns message when no papers found", async () => {
      mockSearchPapers.mockResolvedValue([]);

      const result = await tools.searchArxiv.execute(
        { query: "nonexistent topic" },
        execOpts
      );

      expect(result).toBe("No papers found matching criteria.");
    });

    it("omits similarity when not present", async () => {
      mockSearchPapers.mockResolvedValue([
        {
          arxiv_code: "2401.00001",
          title: "Test Paper",
          authors: "Author",
          published: "2024-01-01",
          abstract: null,
        },
      ]);

      const result = await tools.searchArxiv.execute(
        { query: "test" },
        execOpts
      );

      expect(result).not.toContain("sim:");
    });
  });

  describe("getPaperSummaries", () => {
    it("formats summaries with markdown headers", async () => {
      mockGetSummaries.mockResolvedValue({
        "2401.12345": "This paper introduces the Transformer...",
        "2401.67890": "We present a novel approach...",
      });

      const result = await tools.getPaperSummaries.execute(
        { arxiv_codes: ["2401.12345", "2401.67890"], resolution: "medium" },
        execOpts
      );

      expect(result).toContain("## 2401.12345");
      expect(result).toContain("This paper introduces the Transformer...");
      expect(result).toContain("## 2401.67890");
      expect(result).toContain("---");
    });

    it("returns message when no summaries found", async () => {
      mockGetSummaries.mockResolvedValue({});

      const result = await tools.getPaperSummaries.execute(
        { arxiv_codes: ["invalid"], resolution: "low" },
        execOpts
      );

      expect(result).toBe("No summaries found for provided codes.");
    });
  });

  describe("fetchPaper", () => {
    it("downloads paper and writes to VFS", async () => {
      const paperContent = "# Paper Title\n\nAbstract...";
      mockFetchPaperMarkdown.mockResolvedValue(paperContent);

      const result = await tools.fetchPaper.execute(
        { arxiv_code: "2401.12345" },
        execOpts
      );

      expect(result).toContain("Downloaded 2401.12345");
      expect(result).toContain("/home/user/papers/2401.12345.md");
      expect(result).toContain(`${paperContent.length} chars`);
      expect(fs.read("/home/user/papers/2401.12345.md")).toBe(paperContent);
    });

    it("returns error when paper not found", async () => {
      mockFetchPaperMarkdown.mockResolvedValue(null);

      const result = await tools.fetchPaper.execute(
        { arxiv_code: "invalid" },
        execOpts
      );

      expect(result).toContain("Error");
      expect(result).toContain("not found");
    });
  });
});
