import { tool } from "ai";
import { z } from "zod";
import { VirtualFileSystem } from "../virtual-fs.js";

export function createFileTools(fs: VirtualFileSystem) {
  const writeFile = tool({
    description: "Write content to a file (creates or overwrites).",
    inputSchema: z.object({
      path: z.string().describe("File path (relative to cwd or absolute)"),
      content: z.string().describe("Complete file content"),
    }),
    execute: async ({ path, content }) => fs.write(path, content),
  });

  const readFile = tool({
    description: "Read contents of a file.",
    inputSchema: z.object({
      path: z.string().describe("File path (relative to cwd or absolute)"),
    }),
    execute: async ({ path }) => fs.read(path),
  });

  const runShell = tool({
    description:
      "Execute a shell command. Supported: ls, rm, pwd, cd, grep [-A NUM] [-B NUM] <pattern> [path].",
    inputSchema: z.object({
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
          // Parse: grep [-A NUM] [-B NUM] PATTERN [PATH]
          const tokens = arg.split(" ");
          let before = 0,
            after = 0;

          while (tokens.length && tokens[0].startsWith("-")) {
            const flag = tokens.shift()!;
            if ((flag === "-A" || flag === "-B") && tokens.length) {
              const val = parseInt(tokens.shift()!, 10);
              if (isNaN(val)) return `Error: ${flag} requires a number`;
              if (flag === "-A") after = val;
              else before = val;
            } else {
              return `Error: Unknown flag ${flag}. Usage: grep [-A NUM] [-B NUM] PATTERN [PATH]`;
            }
          }

          if (!tokens.length) {
            return "Usage: grep [-A NUM] [-B NUM] PATTERN [PATH]";
          }
          return fs.grep(tokens[0], tokens[1], before, after);
        }
        default:
          return `Error: Command '${cmd}' not implemented in virtual sandbox.`;
      }
    },
  });

  return { writeFile, readFile, runShell };
}
