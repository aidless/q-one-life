import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import test from "node:test";
import {
  canonicalJson,
  channelForVersion,
  compareVersions,
  linuxUpdateRequiresManualInstall,
  SignedUpdateManifest,
  UpdatePayload,
  verifyUpdateManifest,
} from "../update-policy";

const { publicKey, privateKey } = generateKeyPairSync("ed25519");
const trustedKeys = {
  "release-2026": publicKey
    .export({ format: "der", type: "spki" })
    .toString("base64"),
};

function payload(version = "1.0.1"): UpdatePayload {
  return {
    schema: "q-one-update-manifest-v1",
    channel: "stable",
    version,
    published_at: "2026-11-01T00:00:00Z",
    minimum_version: "0.9.0",
    metadata: {
      name: "latest-linux.yml",
      target: "linux-x64",
      url: "https://aidless.github.io/q-one-life/updates/latest-linux.yml",
      bytes: 100,
      sha256: "a".repeat(64),
      sha512: "b".repeat(128),
    },
    artifacts: [
      {
        name: "Q-One-1.0.1-linux-x86_64.AppImage",
        platform: "linux",
        arch: "x64",
        kind: "appimage",
        rollback: false,
        url: "https://github.com/aidless/q-one-life/releases/download/v1.0.1/Q-One-1.0.1-linux-x86_64.AppImage",
        bytes: 600_000_000,
        sha256: "c".repeat(64),
        sha512: "d".repeat(128),
      },
      {
        name: "Q-One-0.9.1-linux-x86_64.AppImage",
        platform: "linux",
        arch: "x64",
        kind: "appimage",
        rollback: true,
        url: "https://github.com/aidless/q-one-life/releases/download/v0.9.1/Q-One-0.9.1-linux-x86_64.AppImage",
        bytes: 590_000_000,
        sha256: "e".repeat(64),
        sha512: "f".repeat(128),
      },
    ],
  };
}

function macPayload(): UpdatePayload {
  return {
    schema: "q-one-update-manifest-v1",
    channel: "stable",
    version: "1.0.1",
    published_at: "2026-11-01T00:00:00Z",
    metadata: {
      name: "latest-mac.yml",
      target: "darwin-arm64",
      url: "https://aidless.github.io/q-one-life/updates/latest-mac.yml",
      bytes: 100,
      sha256: "a".repeat(64),
      sha512: "b".repeat(128),
    },
    artifacts: [
      {
        name: "Q-One-1.0.1-mac-arm64.dmg",
        platform: "darwin",
        arch: "arm64",
        kind: "dmg",
        rollback: false,
        url: "https://github.com/aidless/q-one-life/releases/download/v1.0.1/Q-One-1.0.1-mac-arm64.dmg",
        bytes: 600_000_000,
        sha256: "c".repeat(64),
        sha512: "d".repeat(128),
      },
      {
        name: "Q-One-1.0.1-mac-arm64.zip",
        platform: "darwin",
        arch: "arm64",
        kind: "zip",
        rollback: false,
        url: "https://github.com/aidless/q-one-life/releases/download/v1.0.1/Q-One-1.0.1-mac-arm64.zip",
        bytes: 590_000_000,
        sha256: "e".repeat(64),
        sha512: "f".repeat(128),
      },
    ],
  };
}

function manifest(value = payload()): SignedUpdateManifest {
  return {
    payload: value,
    signatures: [
      {
        key_id: "release-2026",
        signature: sign(
          null,
          Buffer.from(canonicalJson(value)),
          privateKey,
        ).toString("base64"),
      },
    ],
  };
}

function verify(value: unknown) {
  return verifyUpdateManifest(value, {
    currentVersion: "1.0.0",
    channel: "stable",
    platform: "linux",
    arch: "x64",
    trustedKeys,
  });
}

test("signed stable update returns one artifact and its rollback", () => {
  const update = verify(manifest());
  assert.equal(update.version, "1.0.1");
  assert.equal(update.artifact.kind, "appimage");
  assert.equal(update.rollback?.name, "Q-One-0.9.1-linux-x86_64.AppImage");
  assert.deepEqual(update.signerIds, ["release-2026"]);
});

test("tampering, untrusted keys, channel confusion, and downgrade fail closed", () => {
  const tampered = manifest();
  tampered.payload.version = "1.0.2";
  assert.throws(() => verify(tampered), /trusted signature/);

  const untrusted = manifest();
  untrusted.signatures[0].key_id = "unknown";
  assert.throws(() => verify(untrusted), /trusted signature/);

  const beta = manifest();
  beta.payload.channel = "beta";
  beta.payload.version = "1.0.1-beta.1";
  assert.throws(() => verify(beta), /channel/);

  const downgrade = manifest(payload("0.9.9"));
  assert.throws(() => verify(downgrade), /not newer/);
});

test("metadata, target artifact, and URL boundaries are enforced", () => {
  const wrongMetadata = manifest();
  wrongMetadata.payload.metadata.name = "latest.yml";
  assert.throws(() => verify(wrongMetadata), /metadata filename/);

  const wrongArtifact = manifest();
  wrongArtifact.payload.artifacts[0].arch = "arm64";
  assert.throws(() => verify(wrongArtifact), /exactly one install artifact/);

  const insecure = manifest();
  insecure.payload.artifacts[0].url =
    "http://aidless.github.io/q-one-life/update.AppImage";
  assert.throws(() => verify(insecure), /artifact list/);

  const lookalike = manifest();
  lookalike.payload.artifacts[0].url =
    "https://aidless.github.io.evil.example/update.AppImage";
  assert.throws(() => verify(lookalike), /artifact list/);
});

test("semantic version and channel helpers distinguish prereleases", () => {
  assert.equal(channelForVersion("1.0.0-beta.2"), "beta");
  assert.equal(channelForVersion("1.0.0"), "stable");
  assert.equal(compareVersions("1.0.0-beta.2", "1.0.0-beta.10"), -1);
  assert.equal(compareVersions("1.0.0", "1.0.0-rc.1"), 1);
});

test("macOS updater selects the signed ZIP rather than the DMG", () => {
  const update = verifyUpdateManifest(
    manifest(macPayload()),
    {
      currentVersion: "1.0.0",
      channel: "stable",
      platform: "darwin",
      arch: "arm64",
      trustedKeys,
    },
  );
  assert.equal(update.artifact.kind, "zip");
  assert.match(update.artifact.name, /\.zip$/);
});

test("Linux update mode distinguishes AppImage from deb even with a stale package type", () => {
  assert.equal(
    linuxUpdateRequiresManualInstall("deb", "/tmp/Q-One.AppImage"),
    false,
  );
  assert.equal(linuxUpdateRequiresManualInstall("deb", undefined), true);
  assert.equal(linuxUpdateRequiresManualInstall("deb", "   "), true);
  assert.equal(linuxUpdateRequiresManualInstall("appimage", undefined), false);
  assert.equal(linuxUpdateRequiresManualInstall(undefined, undefined), false);
});
