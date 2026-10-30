import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { SafeStorageBackend, SecretStore } from "../secure-store";

class FakeBackend implements SafeStorageBackend {
  constructor(
    private readonly available = true,
    private readonly backend = "gnome_libsecret",
  ) {}

  async isAsyncEncryptionAvailable(): Promise<boolean> {
    return this.available;
  }

  getSelectedStorageBackend(): string {
    return this.backend;
  }

  async encryptStringAsync(value: string): Promise<Buffer> {
    return Buffer.from(`encrypted:${value.split("").reverse().join("")}`, "utf8");
  }

  async decryptStringAsync(value: Buffer): Promise<{
    result: string;
    shouldReEncrypt: boolean;
  }> {
    const text = value.toString("utf8");
    assert.ok(text.startsWith("encrypted:"));
    return {
      result: text.slice("encrypted:".length).split("").reverse().join(""),
      shouldReEncrypt: false,
    };
  }
}

test("secure store persists encrypted values atomically", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-secret-"));
  const file = path.join(folder, "secrets.json");
  const store = new SecretStore(file, new FakeBackend());
  assert.equal((await store.status()).persistent, true);
  await store.set("cloud_key", "secret-value");
  assert.equal(await store.get("cloud_key"), "secret-value");
  assert.doesNotMatch(await fs.readFile(file, "utf8"), /secret-value/);
  await store.delete("cloud_key");
  assert.equal(await store.get("cloud_key"), undefined);
});

test("basic_text backend remains memory-only and is never persisted", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-secret-"));
  const file = path.join(folder, "secrets.json");
  const store = new SecretStore(file, new FakeBackend(true, "basic_text"));
  await store.set("cloud_key", "session-only");
  assert.equal(await store.get("cloud_key"), "session-only");
  await assert.rejects(fs.stat(file));
  assert.deepEqual(await store.status(), {
    available: true,
    backend: "basic_text",
    persistent: false,
  });
});
