import assert from "node:assert/strict";
import { createHash, generateKeyPairSync, sign } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  canonicalJson,
  SignedUpdateManifest,
  UpdatePayload,
} from "../update-policy";
import { UpdaterLike } from "../update-controller";
import { UpdateController } from "../update-controller";

const { publicKey, privateKey } = generateKeyPairSync("ed25519");
const trustedKeys = {
  test: publicKey.export({ format: "der", type: "spki" }).toString("base64"),
};

function manifest(
  metadata: Buffer,
  artifact: Buffer,
  rollback?: Buffer,
): SignedUpdateManifest {
  const payload: UpdatePayload = {
    schema: "q-one-update-manifest-v1",
    channel: "stable",
    version: "1.0.1",
    published_at: "2026-11-01T00:00:00Z",
    metadata: {
      name: "latest-linux.yml",
      target: "linux-x64",
      url: "https://aidless.github.io/q-one-life/updates/latest-linux.yml",
      bytes: metadata.length,
      sha256: createHash("sha256").update(metadata).digest("hex"),
      sha512: createHash("sha512").update(metadata).digest("hex"),
    },
    artifacts: [
      {
        name: "Q-One-1.0.1-linux-x86_64.AppImage",
        platform: "linux",
        arch: "x64",
        kind: "appimage",
        rollback: false,
        url: "https://github.com/aidless/q-one-life/releases/download/v1.0.1/Q-One-1.0.1-linux-x86_64.AppImage",
        bytes: artifact.length,
        sha256: createHash("sha256").update(artifact).digest("hex"),
        sha512: createHash("sha512").update(artifact).digest("hex"),
      },
      ...(rollback
        ? [
            {
              name: "Q-One-0.9.1-linux-x86_64.AppImage",
              platform: "linux" as const,
              arch: "x64" as const,
              kind: "appimage" as const,
              rollback: true,
              url: "https://github.com/aidless/q-one-life/releases/download/v1.0.1/Q-One-0.9.1-linux-x86_64.AppImage",
              bytes: rollback.length,
              sha256: createHash("sha256").update(rollback).digest("hex"),
              sha512: createHash("sha512").update(rollback).digest("hex"),
            },
          ]
        : []),
    ],
  };
  return {
    payload,
    signatures: [
      {
        key_id: "test",
        signature: sign(null, Buffer.from(canonicalJson(payload)), privateKey).toString("base64"),
      },
    ],
  };
}

function fetchFor(signed: SignedUpdateManifest, metadata: Buffer): typeof fetch {
  return async (input) => {
    const url = String(input);
    if (url.endsWith("/manifest.json")) {
      return new Response(JSON.stringify(signed), { status: 200 });
    }
    if (url.endsWith("/latest-linux.yml")) {
      return new Response(new Uint8Array(metadata), { status: 200 });
    }
    return new Response("missing", { status: 404 });
  };
}

class FakeUpdater implements UpdaterLike {
  autoDownload = true;
  autoInstallOnAppQuit = true;
  allowPrerelease = true;
  allowDowngrade = true;
  disableDifferentialDownload = false;
  channel: string | null = null;
  feed = "";
  checkedVersion = "1.0.1";
  downloadedFile = "";
  listeners = new Map<string, ((value: unknown) => void)[]>();
  setFeedURL(options: { provider: "generic"; url: string }): void {
    assert.equal(options.provider, "generic");
    this.feed = options.url;
  }
  async checkForUpdates() {
    assert.match(this.feed, /^http:\/\/127\.0\.0\.1:\d+\/$/);
    return { updateInfo: { version: this.checkedVersion } };
  }
  async downloadUpdate(): Promise<string[]> {
    this.emit("update-downloaded", {
      version: "1.0.1",
      downloadedFile: this.downloadedFile,
    });
    return [this.downloadedFile];
  }
  quitAndInstall(): void {}
  on(event: string, listener: (value: unknown) => void): unknown {
    const values = this.listeners.get(event) ?? [];
    values.push(listener);
    this.listeners.set(event, values);
    return this;
  }
  emit(event: string, value: unknown): void {
    for (const listener of this.listeners.get(event) ?? []) listener(value);
  }
}

function options(updater: FakeUpdater, metadata: Buffer, artifact: Buffer) {
  return {
    currentVersion: "1.0.0",
    channel: "stable" as const,
    platform: "linux" as const,
    arch: "x64" as const,
    manifestUrl: "https://aidless.github.io/q-one-life/updates/stable/manifest.json",
    trustedKeys,
    updater,
    fetchImpl: fetchFor(manifest(metadata, artifact), metadata),
  };
}

test("controller checks signed metadata, verifies the downloaded artifact, and becomes ready", async () => {
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), "qone-update-controller-"));
  const artifact = Buffer.from("verified update");
  const metadata = Buffer.from("version: 1.0.1\n");
  const file = path.join(parent, "update.AppImage");
  await fs.writeFile(file, artifact);
  const updater = new FakeUpdater();
  updater.downloadedFile = file;
  const controller = new UpdateController(options(updater, metadata, artifact));
  try {
    const available = await controller.check();
    assert.equal(available.phase, "available");
    assert.equal(available.available_version, "1.0.1");
    const ready = await controller.download();
    assert.equal(ready.phase, "ready");
    assert.equal(ready.can_install, true);
  } finally {
    await controller.dispose();
    await fs.rm(parent, { recursive: true, force: true });
  }
});

test("controller refuses a downloaded file that no longer matches the signed hash", async () => {
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), "qone-update-controller-"));
  const artifact = Buffer.from("verified update");
  const metadata = Buffer.from("version: 1.0.1\n");
  const file = path.join(parent, "update.AppImage");
  await fs.writeFile(file, Buffer.from("tampered update"));
  const updater = new FakeUpdater();
  updater.downloadedFile = file;
  const controller = new UpdateController(options(updater, metadata, artifact));
  try {
    await controller.check();
    const result = await controller.download();
    assert.equal(result.phase, "error");
    assert.equal(result.error_code, "UPDATE_ARTIFACT_MISMATCH");
  } finally {
    await controller.dispose();
    await fs.rm(parent, { recursive: true, force: true });
  }
});

test("missing trusted keys keep the controller unavailable", async () => {
  const updater = new FakeUpdater();
  const controller = new UpdateController({
    ...options(updater, Buffer.from("version: 1.0.1\n"), Buffer.from("update")),
    trustedKeys: {},
  });
  const status = await controller.check();
  assert.equal(status.phase, "unavailable");
  assert.equal(status.error_code, "UPDATE_NOT_CONFIGURED");
  await controller.dispose();
});

test("controller exposes only the signed rollback artifact URL", async () => {
  const artifact = Buffer.from("verified update");
  const rollback = Buffer.from("verified rollback");
  const metadata = Buffer.from("version: 1.0.1\n");
  const updater = new FakeUpdater();
  const controller = new UpdateController({
    ...options(updater, metadata, artifact),
    fetchImpl: fetchFor(manifest(metadata, artifact, rollback), metadata),
  });
  try {
    const status = await controller.check();
    assert.equal(status.rollback_available, true);
    assert.match(
      controller.downloadUrl("rollback") ?? "",
      /Q-One-0\.9\.1-linux-x86_64\.AppImage$/,
    );
  } finally {
    await controller.dispose();
  }
});
