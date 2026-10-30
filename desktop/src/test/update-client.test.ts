import assert from "node:assert/strict";
import { createHash, generateKeyPairSync, sign } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  parseTrustedUpdateKeys,
  prepareVerifiedUpdate,
  serveVerifiedMetadata,
  verifyArtifactFile,
  UpdateClientError,
} from "../update-client";
import {
  canonicalJson,
  SignedUpdateManifest,
  UpdatePayload,
} from "../update-policy";

const { publicKey, privateKey } = generateKeyPairSync("ed25519");
const trustedKeys = {
  "test-release": publicKey.export({ format: "der", type: "spki" }).toString("base64"),
};

function payload(metadata: Buffer, artifactBytes: Buffer): UpdatePayload {
  return {
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
        bytes: artifactBytes.length,
        sha256: createHash("sha256").update(artifactBytes).digest("hex"),
        sha512: createHash("sha512").update(artifactBytes).digest("hex"),
      },
    ],
  };
}

function manifest(value: UpdatePayload): SignedUpdateManifest {
  return {
    payload: value,
    signatures: [
      {
        key_id: "test-release",
        signature: sign(null, Buffer.from(canonicalJson(value)), privateKey).toString("base64"),
      },
    ],
  };
}

function fakeFetch(manifestValue: unknown, metadata: Buffer): typeof fetch {
  return async (input) => {
    const url = String(input);
    if (url.endsWith("/manifest.json")) {
      return new Response(JSON.stringify(manifestValue), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.endsWith("/latest-linux.yml")) {
      return new Response(new Uint8Array(metadata), {
        status: 200,
        headers: { "Content-Type": "text/yaml" },
      });
    }
    return new Response("not found", { status: 404 });
  };
}

function options(metadata: Buffer, artifactBytes: Buffer) {
  const value = payload(metadata, artifactBytes);
  return {
    manifestUrl: "https://aidless.github.io/q-one-life/updates/stable/manifest.json",
    currentVersion: "1.0.0",
    channel: "stable" as const,
    platform: "linux" as const,
    arch: "x64" as const,
    trustedKeys,
    fetchImpl: fakeFetch(manifest(value), metadata),
  };
}

test("signed manifest and exact metadata bytes are accepted", async () => {
  const metadata = Buffer.from("version: 1.0.1\npath: Q-One-1.0.1-linux-x86_64.AppImage\n");
  const artifact = Buffer.from("update artifact");
  const prepared = await prepareVerifiedUpdate(options(metadata, artifact));
  assert.equal(prepared.verified.version, "1.0.1");
  assert.deepEqual(prepared.metadata, metadata);
});

test("metadata and artifact tampering fail closed", async () => {
  const metadata = Buffer.from("version: 1.0.1\n");
  const artifact = Buffer.from("update artifact");
  const badMetadataOptions = options(metadata, artifact);
  badMetadataOptions.fetchImpl = fakeFetch(
    manifest(payload(metadata, artifact)),
    Buffer.from("version: 1.0.2\n"),
  );
  await assert.rejects(
    () => prepareVerifiedUpdate(badMetadataOptions),
    (error: unknown) =>
      error instanceof UpdateClientError && error.code === "UPDATE_METADATA_MISMATCH",
  );

  const temp = await fs.mkdtemp(path.join(os.tmpdir(), "qone-update-client-"));
  const file = path.join(temp, "artifact");
  try {
    await fs.writeFile(file, Buffer.from("tampered artifact"));
    await assert.rejects(
      () =>
        verifyArtifactFile(file, {
          bytes: artifact.length,
          sha256: createHash("sha256").update(artifact).digest("hex"),
          sha512: createHash("sha512").update(artifact).digest("hex"),
        }),
      (error: unknown) =>
        error instanceof UpdateClientError && error.code === "UPDATE_ARTIFACT_MISMATCH",
    );
  } finally {
    await fs.rm(temp, { recursive: true, force: true });
  }
});

test("trusted key file and loopback metadata feed are strict", async () => {
  const parsed = parseTrustedUpdateKeys(
    JSON.stringify({ schema: "q-one-update-public-keys-v1", keys: trustedKeys }),
  );
  assert.equal(parsed["test-release"], trustedKeys["test-release"]);
  assert.throws(() => parseTrustedUpdateKeys('{"schema":"wrong","keys":{}}'));

  const bytes = Buffer.from("version: 1.0.1\n");
  const feed = await serveVerifiedMetadata("latest-linux.yml", bytes);
  try {
    const response = await fetch(`${feed.url}latest-linux.yml`);
    assert.equal(response.status, 200);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), bytes);
    const missing = await fetch(`${feed.url}other.yml`);
    assert.equal(missing.status, 404);
  } finally {
    await feed.close();
  }
});
