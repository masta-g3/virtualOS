import { tool } from "ai";
import { z } from "zod";
import { VirtualFileSystem } from "../virtual-fs.js";

export function createFileTools(fs: VirtualFileSystem) {
  const writeFile = tool({
    description: "Write content to a file (creates or overwrites).",
    parameters: z.object({
      path: z.string().describe("File path (relative to cwd or absolute)"),
      content: z.string().describe("Complete file content"),
    }),
    execute: async ({ path, content }) => fs.write(path, content),
  });

  const readFile = tool({
    description: "Read contents of a file.",
    parameters: z.object({
      path: z.string().describe("File path (relative to cwd or absolute)"),
    }),
    execute: async ({ path }) => fs.read(path),
  });

  const runShell = tool({
    description:
      "Execute a shell command. Supported: ls, rm, pwd, cd, grep <pattern> [path].",
    parameters: z.object({
      command: z.string().describe("Shell command to execute"),
    }),
    execute: async ({ command }) => {
      const parts = command.split(" ");
      const cmd = parts[0];
      const arg = parts.slice(1).join(" ");

      switch (cmd) {
        case "ls":
          return fs.listDir(arg || ".");
        case "pwd":
          return fs.cwd;
        case "cd":
          return fs.cd(arg);
        case "rm":
          return fs.delete(arg);
        case "grep": {
          const args = arg.split(" ");
          if (args.length === 0 || !args[0]) {
            return "Error: grep requires a pattern. Usage: grep <pattern> [path]";
          }
          return fs.grep(args[0], args[1]);
        }
        default:
          return `Error: Command '${cmd}' not implemented in virtual sandbox.`;
      }
    },
  });

  return { writeFile, readFile, runShell };
}
