import { describe, it, expect, beforeEach } from "vitest";
import { VirtualFileSystem } from "../src/virtual-fs.js";

const VIRTUAL_ROOT = "/home/user";

describe("VirtualFileSystem", () => {
  let fs: VirtualFileSystem;

  beforeEach(() => {
    fs = new VirtualFileSystem();
  });

  describe("path resolution", () => {
    it("resolves absolute paths unchanged", () => {
      fs.write("/foo/bar.txt", "test");
      expect(fs.read("/foo/bar.txt")).toBe("test");
    });

    it("resolves relative paths from cwd", () => {
      fs.cwd = "/home/user";
      fs.write("docs/readme.md", "content");
      expect(fs.read("/home/user/docs/readme.md")).toBe("content");
    });

    it("resolves parent directory references", () => {
      fs.cwd = "/home/user/docs";
      fs.write("../readme.md", "parent");
      expect(fs.read("/home/user/readme.md")).toBe("parent");
    });

    it("resolves current directory dot", () => {
      fs.cwd = "/home/user";
      fs.write("./file.txt", "dot");
      expect(fs.read("/home/user/file.txt")).toBe("dot");
    });

    it("resolves multiple parent refs", () => {
      fs.cwd = "/home/user/a/b/c";
      fs.write("../../file.txt", "deep");
      expect(fs.read("/home/user/a/file.txt")).toBe("deep");
    });
  });

  describe("file operations", () => {
    it("write creates file", () => {
      const result = fs.write("test.txt", "hello");
      expect(result).toContain("Successfully wrote");
      expect(fs.files.get(`${VIRTUAL_ROOT}/test.txt`)).toBe("hello");
    });

    it("write overwrites file", () => {
      fs.write("test.txt", "first");
      fs.write("test.txt", "second");
      expect(fs.files.get(`${VIRTUAL_ROOT}/test.txt`)).toBe("second");
    });

    it("read returns file content", () => {
      fs.files.set(`${VIRTUAL_ROOT}/test.txt`, "content");
      expect(fs.read("test.txt")).toBe("content");
    });

    it("read missing file returns error", () => {
      const result = fs.read("nonexistent.txt");
      expect(result).toContain("Error");
      expect(result).toContain("does not exist");
    });

    it("delete removes file", () => {
      fs.files.set(`${VIRTUAL_ROOT}/temp.txt`, "data");
      const result = fs.delete("temp.txt");
      expect(result).toContain("Deleted");
      expect(fs.files.has(`${VIRTUAL_ROOT}/temp.txt`)).toBe(false);
    });

    it("delete missing file returns error", () => {
      const result = fs.delete("nonexistent.txt");
      expect(result).toContain("Error");
    });
  });

  describe("directory listing", () => {
    it("empty directory returns message", () => {
      const result = fs.listDir("/empty");
      expect(result).toBe("(empty directory)");
    });

    it("lists files in directory", () => {
      fs.files.set(`${VIRTUAL_ROOT}/a.txt`, "a");
      fs.files.set(`${VIRTUAL_ROOT}/b.txt`, "b");
      const listing = fs.listDir(VIRTUAL_ROOT);
      expect(listing).toContain("a.txt");
      expect(listing).toContain("b.txt");
    });

    it("excludes nested files", () => {
      fs.files.set(`${VIRTUAL_ROOT}/top.txt`, "top");
      fs.files.set(`${VIRTUAL_ROOT}/sub/nested.txt`, "nested");
      const listing = fs.listDir(VIRTUAL_ROOT);
      expect(listing).toContain("top.txt");
      expect(listing).not.toContain("nested.txt");
    });
  });

  describe("cd command", () => {
    it("changes cwd to absolute path", () => {
      fs.cd("/tmp");
      expect(fs.cwd).toBe("/tmp");
    });

    it("changes cwd to relative path", () => {
      fs.cwd = "/home/user";
      fs.cd("docs");
      expect(fs.cwd).toBe("/home/user/docs");
    });

    it("handles parent navigation", () => {
      fs.cwd = "/home/user/docs";
      fs.cd("..");
      expect(fs.cwd).toBe("/home/user");
    });
  });

  describe("grep", () => {
    it("finds matching lines", () => {
      fs.files.set(`${VIRTUAL_ROOT}/code.py`, "def foo():\n    return 42\ndef bar():\n    return 0");
      const result = fs.grep("def");
      expect(result).toContain("code.py:1:def foo():");
      expect(result).toContain("code.py:3:def bar():");
    });

    it("returns no matches message when pattern not found", () => {
      fs.files.set(`${VIRTUAL_ROOT}/test.txt`, "hello world");
      const result = fs.grep("xyz");
      expect(result).toBe("No matches found.");
    });

    it("searches within specified path", () => {
      fs.files.set(`${VIRTUAL_ROOT}/a/file.txt`, "match here");
      fs.files.set(`${VIRTUAL_ROOT}/b/file.txt`, "match there");
      const result = fs.grep("match", "/home/user/a");
      expect(result).toContain("a/file.txt");
      expect(result).not.toContain("b/file.txt");
    });

    it("supports regex patterns", () => {
      fs.files.set(`${VIRTUAL_ROOT}/test.txt`, "foo123\nbar456\nbaz");
      const result = fs.grep("\\d+");
      expect(result).toContain("test.txt:1:foo123");
      expect(result).toContain("test.txt:2:bar456");
      expect(result).not.toContain("baz");
    });

    it("shows context lines with before and after", () => {
      fs.files.set(`${VIRTUAL_ROOT}/code.py`, "line1\nline2\nmatch\nline4\nline5");
      const result = fs.grep("match", undefined, 1, 1);
      expect(result).toContain("code.py:2-line2");
      expect(result).toContain("code.py:3:match");
      expect(result).toContain("code.py:4-line4");
    });

    it("separates non-adjacent context groups", () => {
      fs.files.set(`${VIRTUAL_ROOT}/test.txt`, "a\nmatch1\nb\nc\nd\nmatch2\ne");
      const result = fs.grep("match", undefined, 0, 1);
      expect(result).toContain("--");
    });

    it("skips .dir markers", () => {
      fs.files.set(`${VIRTUAL_ROOT}/subdir/.dir`, "");
      fs.files.set(`${VIRTUAL_ROOT}/test.txt`, "content");
      const result = fs.grep("content");
      expect(result).not.toContain(".dir");
    });

    it("searches specific file only", () => {
      fs.files.set(`${VIRTUAL_ROOT}/a.txt`, "match");
      fs.files.set(`${VIRTUAL_ROOT}/b.txt`, "match");
      const result = fs.grep("match", `${VIRTUAL_ROOT}/a.txt`);
      expect(result).toContain("a.txt");
      expect(result).not.toContain("b.txt");
    });
  });

  describe("edge cases", () => {
    it("handles trailing slashes", () => {
      fs.write("/home/user/", "test");
      // Path normalization should work
      expect(fs.files.size).toBeGreaterThan(0);
    });

    it("handles root traversal attempts", () => {
      fs.cwd = "/home";
      fs.write("../../../etc/passwd", "hack");
      // Should resolve without going above root
      expect(fs.files.has("/etc/passwd")).toBe(true);
    });

    it("handles empty relative path", () => {
      fs.cwd = "/home/user";
      const result = fs.cd("");
      expect(result).toContain("/home/user");
    });
  });

  describe("loadFromDisk", () => {
    it("handles non-existent directory gracefully", () => {
      fs.loadFromDisk("/nonexistent/path");
      expect(fs.files.size).toBe(0);
    });
  });
});
