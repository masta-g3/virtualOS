import { readdirSync, readFileSync } from "fs";
import { join } from "path";

const VIRTUAL_ROOT = "/home/user";

export class VirtualFileSystem {
  files: Map<string, string> = new Map();
  cwd: string = VIRTUAL_ROOT;

  private resolve(path: string): string {
    let resolved: string;
    if (path.startsWith("/")) {
      resolved = path;
    } else {
      resolved = `${this.cwd.replace(/\/$/, "")}/${path}`;
    }
    // Normalize . and ..
    const parts: string[] = [];
    for (const part of resolved.split("/")) {
      if (part === "..") {
        if (parts.length > 0) {
          parts.pop();
        }
      } else if (part && part !== ".") {
        parts.push(part);
      }
    }
    return "/" + parts.join("/");
  }

  write(path: string, content: string): string {
    const fullPath = this.resolve(path);
    this.files.set(fullPath, content);
    return `Successfully wrote ${content.length} chars to ${fullPath}`;
  }

  read(path: string): string {
    const fullPath = this.resolve(path);
    const content = this.files.get(fullPath);
    if (content === undefined) {
      return `Error: File ${fullPath} does not exist.`;
    }
    return content;
  }

  listDir(path: string = "."): string {
    const targetDir = this.resolve(path);
    const matches: string[] = [];
    for (const filePath of this.files.keys()) {
      if (filePath.startsWith(targetDir)) {
        const relative = filePath.slice(targetDir.length).replace(/^\//, "");
        if (relative && !relative.includes("/")) {
          matches.push(relative);
        }
      }
    }
    if (matches.length === 0) {
      return "(empty directory)";
    }
    return matches.join("\n");
  }

  delete(path: string): string {
    const fullPath = this.resolve(path);
    if (this.files.has(fullPath)) {
      this.files.delete(fullPath);
      return `Deleted ${fullPath}`;
    }
    return `Error: File ${fullPath} not found`;
  }

  cd(path: string): string {
    this.cwd = this.resolve(path || ".");
    return `Changed directory to ${this.cwd}`;
  }

  grep(pattern: string, path?: string): string {
    const regex = new RegExp(pattern);
    const results: string[] = [];
    const targetDir = path ? this.resolve(path) : this.cwd;

    for (const [filePath, content] of this.files.entries()) {
      if (!filePath.startsWith(targetDir)) continue;
      const lines = content.split("\n");
      for (let i = 0; i < lines.length; i++) {
        if (regex.test(lines[i])) {
          results.push(`${filePath}:${i + 1}:${lines[i]}`);
        }
      }
    }

    return results.length > 0 ? results.join("\n") : "No matches found.";
  }

  loadFromDisk(basePath: string): void {
    const walk = (dir: string) => {
      let entries;
      try {
        entries = readdirSync(join(basePath, dir), { withFileTypes: true });
      } catch {
        return; // Directory doesn't exist - no-op (expected on Vercel)
      }
      for (const entry of entries) {
        const relativePath = dir ? `${dir}/${entry.name}` : entry.name;
        if (entry.isDirectory()) {
          walk(relativePath);
        } else {
          const content = readFileSync(join(basePath, relativePath), "utf-8");
          this.files.set(`${VIRTUAL_ROOT}/${relativePath}`, content);
        }
      }
    };
    walk("");
  }
}
