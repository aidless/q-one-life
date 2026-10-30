import { createHash } from "node:crypto";
import { promises as fs, constants as fsConstants } from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";

interface FileDigest {
  path: string;
  size: number;
  sha256: string;
}

export interface MigrationResult {
  status: "migrated" | "not-needed";
  source?: string;
  target?: string;
  files?: number;
}

export function legacyDataPath(home = os.homedir()): string {
  return path.join(home, ".local", "share", "q-one");
}

export async function directoryIsEmpty(directory: string): Promise<boolean> {
  try {
    return (await fs.readdir(directory)).length === 0;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return true;
    throw error;
  }
}

async function digestTree(root: string): Promise<FileDigest[]> {
  const result: FileDigest[] = [];
  async function visit(current: string): Promise<void> {
    const entries = await fs.readdir(current, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await visit(absolute);
      } else if (entry.isFile()) {
        const bytes = await fs.readFile(absolute);
        result.push({
          path: path.relative(root, absolute).split(path.sep).join("/"),
          size: bytes.byteLength,
          sha256: createHash("sha256").update(bytes).digest("hex"),
        });
      }
    }
  }
  await visit(root);
  return result;
}

async function legacyServerIsRunning(): Promise<boolean> {
  return new Promise((resolve) => {
    const request = http.get(
      { hostname: "127.0.0.1", port: 8765, path: "/api/health", timeout: 700 },
      (response) => {
        response.resume();
        resolve(response.statusCode === 200);
      },
    );
    request.on("timeout", () => request.destroy());
    request.on("error", () => resolve(false));
  });
}

export async function migrateLegacyData(
  source: string,
  target: string,
  options: { checkLegacyServer?: boolean } = {},
): Promise<MigrationResult> {
  if (!(await directoryIsEmpty(target))) return { status: "not-needed" };
  try {
    const stat = await fs.stat(source);
    if (!stat.isDirectory()) return { status: "not-needed" };
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return { status: "not-needed" };
    throw error;
  }
  if ((options.checkLegacyServer ?? true) && (await legacyServerIsRunning())) {
    throw new Error("legacy Q-One is still running on port 8765");
  }

  const parent = path.dirname(target);
  await fs.mkdir(parent, { recursive: true, mode: 0o700 });
  const staging = path.join(parent, `.migration-${process.pid}-${Date.now()}`);
  await fs.cp(source, staging, {
    recursive: true,
    errorOnExist: true,
    force: false,
    preserveTimestamps: true,
  });

  const sourceDigests = await digestTree(source);
  const stagingDigests = await digestTree(staging);
  if (JSON.stringify(sourceDigests) !== JSON.stringify(stagingDigests)) {
    await fs.rm(staging, { recursive: true, force: true });
    throw new Error("migration verification failed");
  }

  const manifestPath = path.join(staging, ".q-one-migration.json");
  const manifest = {
    version: 1,
    source,
    migrated_at: new Date().toISOString(),
    files: stagingDigests,
  };
  const manifestHandle = await fs.open(manifestPath, fsConstants.O_WRONLY | fsConstants.O_CREAT | fsConstants.O_EXCL, 0o600);
  try {
    await manifestHandle.writeFile(`${JSON.stringify(manifest, null, 2)}\n`, "utf8");
    await manifestHandle.sync();
  } finally {
    await manifestHandle.close();
  }

  if ((await fs.readdir(target).catch(() => [] as string[])).length === 0) {
    await fs.rmdir(target).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== "ENOENT") throw error;
    });
  }
  await fs.rename(staging, target);
  return { status: "migrated", source, target, files: stagingDigests.length };
}
