import { promises as fs } from "node:fs";
import path from "node:path";

export interface SafeStorageBackend {
  isAsyncEncryptionAvailable(): Promise<boolean>;
  getSelectedStorageBackend?(): string;
  encryptStringAsync(value: string): Promise<Buffer>;
  decryptStringAsync(value: Buffer): Promise<{
    result: string;
    shouldReEncrypt: boolean;
  }>;
}

interface SecretFile {
  version: 1;
  entries: Record<string, string>;
}

export interface SecretStoreStatus {
  available: boolean;
  backend: string;
  persistent: boolean;
}

/**
 * Keeps secrets in the OS credential backend when it is available. A
 * `basic_text` backend is treated as non-secure: the value remains only in
 * process memory and the UI must tell the user that it will not survive a
 * restart.
 */
export class SecretStore {
  private readonly memory = new Map<string, string>();

  constructor(
    private readonly filePath: string,
    private readonly backend: SafeStorageBackend,
  ) {}

  async status(): Promise<SecretStoreStatus> {
    const available = await this.backend.isAsyncEncryptionAvailable();
    const backend =
      this.backend.getSelectedStorageBackend?.() ||
      (available ? "unknown" : "unavailable");
    const persistent = available && backend !== "basic_text";
    return { available, backend, persistent };
  }

  async get(name: string): Promise<string | undefined> {
    if (this.memory.has(name)) return this.memory.get(name);
    if (!(await this.status()).persistent) return undefined;
    try {
      const file = await this.readFile();
      const encoded = file.entries[name];
      if (!encoded) return undefined;
      const decrypted = await this.backend.decryptStringAsync(
        Buffer.from(encoded, "base64"),
      );
      if (decrypted.shouldReEncrypt) {
        file.entries[name] = (
          await this.backend.encryptStringAsync(decrypted.result)
        ).toString("base64");
        await this.writeFile(file);
      }
      return decrypted.result;
    } catch {
      // A damaged credential file must not prevent the app from opening. The
      // user can re-enter the affected secret from settings.
      return undefined;
    }
  }

  async set(name: string, value: string): Promise<SecretStoreStatus> {
    if (!value) return this.delete(name);
    const status = await this.status();
    this.memory.set(name, value);
    if (!status.persistent) return status;
    const file = await this.readFile();
    file.entries[name] = (
      await this.backend.encryptStringAsync(value)
    ).toString("base64");
    await this.writeFile(file);
    return status;
  }

  async delete(name: string): Promise<SecretStoreStatus> {
    this.memory.delete(name);
    const status = await this.status();
    if (!status.persistent) return status;
    const file = await this.readFile();
    if (name in file.entries) {
      delete file.entries[name];
      await this.writeFile(file);
    }
    return status;
  }

  private async readFile(): Promise<SecretFile> {
    try {
      const parsed = JSON.parse(await fs.readFile(this.filePath, "utf8")) as Partial<SecretFile>;
      if (parsed.version !== 1 || !parsed.entries || typeof parsed.entries !== "object") {
        return { version: 1, entries: {} };
      }
      return { version: 1, entries: parsed.entries as Record<string, string> };
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") {
        return { version: 1, entries: {} };
      }
      throw error;
    }
  }

  private async writeFile(file: SecretFile): Promise<void> {
    await fs.mkdir(path.dirname(this.filePath), { recursive: true, mode: 0o700 });
    const temporary = `${this.filePath}.${process.pid}.tmp`;
    try {
      await fs.writeFile(temporary, JSON.stringify(file), { mode: 0o600 });
      await fs.rename(temporary, this.filePath);
    } finally {
      await fs.rm(temporary, { force: true }).catch(() => undefined);
    }
  }
}
