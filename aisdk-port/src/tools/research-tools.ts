import { tool } from "ai";
import { z } from "zod";
import { VirtualFileSystem } from "../virtual-fs.js";
import {
  searchPapers,
  getSummaries,
  fetchPaperMarkdown,
} from "../lib/llmpedia.js";

export function createResearchTools(fs: VirtualFileSystem) {
  const searchArxiv = tool({
    description: `Search arXiv papers in LLMpedia database.
Use semantic query for conceptual search, or filters for specific criteria.
Returns: arxiv_code, title, authors, published date, abstract snippet.`,
    parameters: z.object({
      query: z.string().optional().describe("Semantic search query"),
      title_contains: z
        .string()
        .optional()
        .describe("Substring match in title"),
      author: z.string().optional().describe("Author name substring"),
      published_after: z.string().optional().describe("ISO date YYYY-MM-DD"),
      published_before: z.string().optional().describe("ISO date YYYY-MM-DD"),
      limit: z.number().default(10).describe("Max results (default 10)"),
    }),
    execute: async (params) => {
      const papers = await searchPapers(params);
      if (papers.length === 0) return "No papers found matching criteria.";
      return papers
        .map(
          (p) =>
            `[${p.arxiv_code}] ${p.title}\n  ${p.authors}\n  ${p.published}${p.similarity ? ` (sim: ${p.similarity})` : ""}`
        )
        .join("\n\n");
    },
  });

  const getPaperSummaries = tool({
    description: `Get summaries for papers at specified detail level.
Resolutions: low (~500 tokens), medium (~1000), high (~2500).`,
    parameters: z.object({
      arxiv_codes: z.array(z.string()).describe("List of arxiv codes"),
      resolution: z.enum(["low", "medium", "high"]).default("medium"),
    }),
    execute: async ({ arxiv_codes, resolution }) => {
      const summaries = await getSummaries(arxiv_codes, resolution);
      if (Object.keys(summaries).length === 0)
        return "No summaries found for provided codes.";
      return Object.entries(summaries)
        .map(([code, summary]) => `## ${code}\n${summary}`)
        .join("\n\n---\n\n");
    },
  });

  const fetchPaper = tool({
    description: `Download full paper markdown to /home/user/papers/{arxiv_code}.md`,
    parameters: z.object({
      arxiv_code: z.string().describe("ArXiv paper code"),
    }),
    execute: async ({ arxiv_code }) => {
      const content = await fetchPaperMarkdown(arxiv_code);
      if (!content) return `Error: Paper ${arxiv_code} not found in archive.`;
      const path = `/home/user/papers/${arxiv_code}.md`;
      fs.write(path, content);
      return `Downloaded ${arxiv_code} to ${path} (${content.length} chars)`;
    },
  });

  return { searchArxiv, getPaperSummaries, fetchPaper };
}
