import { describe, it, expect, beforeEach } from "vitest";
import { VirtualFileSystem } from "../src/virtual-fs.js";
import { createFileTools } from "../src/tools/file-tools.js";

const VIRTUAL_ROOT = "/home/user";

describe("file tools", () => {
  let fs: VirtualFileSystem;
  let tools: ReturnType<typeof createFileTools>;

  beforeEach(() => {
    fs = new VirtualFileSystem();
    tools = createFileTools(fs);
  });

  describe("writeFile", () => {
    it("creates file via VFS", async () => {
      const result = await tools.writeFile.execute(
        { path: "test.py", content: "print('hi')" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toContain("Successfully wrote");
      expect(fs.files.get(`${VIRTUAL_ROOT}/test.py`)).toBe("print('hi')");
    });
  });

  describe("readFile", () => {
    it("reads file via VFS", async () => {
      fs.files.set(`${VIRTUAL_ROOT}/test.txt`, "content");
      const result = await tools.readFile.execute(
        { path: "test.txt" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toBe("content");
    });
  });

  describe("runShell", () => {
    it("ls lists files", async () => {
      fs.write("file.txt", "content");
      const result = await tools.runShell.execute(
        { command: "ls" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toContain("file.txt");
    });

    it("pwd returns cwd", async () => {
      fs.cwd = "/home/user";
      const result = await tools.runShell.execute(
        { command: "pwd" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toBe("/home/user");
    });

    it("cd changes directory", async () => {
      await tools.runShell.execute(
        { command: "cd /tmp" },
        { toolCallId: "1", messages: [] }
      );
      expect(fs.cwd).toBe("/tmp");
    });

    it("rm deletes file", async () => {
      fs.write("temp.txt", "data");
      const result = await tools.runShell.execute(
        { command: "rm temp.txt" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toContain("Deleted");
      expect(fs.files.has(`${VIRTUAL_ROOT}/temp.txt`)).toBe(false);
    });

    it("unsupported command returns error", async () => {
      const result = await tools.runShell.execute(
        { command: "wget http://example.com" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toContain("not implemented");
    });

    it("grep finds matching lines", async () => {
      fs.write("test.py", "def hello():\n    pass\ndef world():");
      const result = await tools.runShell.execute(
        { command: "grep def" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toContain("def hello():");
      expect(result).toContain("def world():");
    });

    it("grep with path searches specific directory", async () => {
      fs.write("a.txt", "match");
      fs.cd("/other");
      fs.write("b.txt", "match");
      const result = await tools.runShell.execute(
        { command: "grep match /home/user" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toContain("a.txt");
      expect(result).not.toContain("b.txt");
    });

    it("grep without pattern returns error", async () => {
      const result = await tools.runShell.execute(
        { command: "grep" },
        { toolCallId: "1", messages: [] }
      );
      expect(result).toContain("Error");
      expect(result).toContain("requires a pattern");
    });
  });
});
