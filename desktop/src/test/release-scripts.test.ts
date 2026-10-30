import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { createHash, generateKeyPairSync } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import test from "node:test";

import { verifyUpdateManifest } from "../update-policy";

const execFileAsync = promisify(execFile);
const desktopDirectory = path.resolve(__dirname, "../..");

test("release manifest generator emits verifiable target metadata", async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "q-one-release-"));
  const release = path.join(root, "release");
  const updates = path.join(root, "updates");
  const evidence = path.join(release, "evidence");
  await fs.mkdir(evidence, { recursive: true });

  const artifactName = "Q-One-1.0.1-linux-x86_64.AppImage";
  const rollbackName = "Q-One-0.9.1-linux-x86_64.AppImage";
  const artifact = Buffer.from("signed-appimage-test-payload");
  const rollback = Buffer.from("signed-rollback-test-payload");
  await fs.writeFile(path.join(release, artifactName), artifact);
  await fs.writeFile(path.join(release, rollbackName), rollback);
  await fs.writeFile(
    path.join(release, "latest-linux.yml"),
    [
      "version: 1.0.1",
      "files:",
      `  - url: ${artifactName}`,
      "    sha512: test",
      `    size: ${artifact.length}`,
      `path: ${artifactName}`,
      "sha512: test",
      "releaseDate: '2026-11-01T00:00:00.000Z'",
      "",
    ].join("\n"),
  );
  const sha256 = createHash("sha256").update(artifact).digest("hex");
  const rollbackSha256 = createHash("sha256").update(rollback).digest("hex");
  await fs.writeFile(
    path.join(evidence, "SHA256SUMS.txt"),
    `${sha256}  ${artifactName}\n${rollbackSha256}  ${rollbackName}\n`,
  );

  const { privateKey } = generateKeyPairSync("ed25519");
  const privateKeyFile = path.join(root, "update-key.pem");
  const publicKeyFile = path.join(root, "update-public-keys.json");
  await fs.writeFile(
    privateKeyFile,
    privateKey.export({ format: "pem", type: "pkcs8" }),
    { mode: 0o600 },
  );

  await execFileAsync(
    process.execPath,
    [
      path.join(desktopDirectory, "scripts", "create-update-manifest.mjs"),
      "--release-dir",
      release,
      "--version",
      "1.0.1",
      "--channel",
      "stable",
      "--platform",
      "linux",
      "--arch",
      "x64",
      "--private-key-file",
      privateKeyFile,
      "--key-id",
      "test-release",
      "--rollback-file",
      path.join(release, rollbackName),
      "--public-key-output",
      publicKeyFile,
      "--output-dir",
      updates,
      "--metadata-base-url",
      "https://aidless.github.io/q-one-life/updates/stable",
      "--artifact-base-url",
      "https://github.com/aidless/q-one-life/releases/download/v1.0.1",
    ],
    { cwd: desktopDirectory },
  );

  const manifest = JSON.parse(
    await fs.readFile(path.join(updates, "manifest.json"), "utf8"),
  );
  const publicKeys = JSON.parse(await fs.readFile(publicKeyFile, "utf8"));
  const verified = verifyUpdateManifest(manifest, {
    currentVersion: "0.7.1",
    channel: "stable",
    platform: "linux",
    arch: "x64",
    trustedKeys: publicKeys.keys,
  });
  assert.equal(verified.metadata.target, "linux-x64");
  assert.equal(verified.metadata.name, "latest-linux.yml");
  assert.equal(verified.rollback?.name, rollbackName);

  await execFileAsync(
    process.execPath,
    [
      path.join(desktopDirectory, "scripts", "verify-release.mjs"),
      "--release-dir",
      release,
      "--manifest",
      path.join(updates, "manifest.json"),
      "--public-keys",
      publicKeyFile,
      "--from-version",
      "0.7.1",
      "--platform",
      "linux",
      "--arch",
      "x64",
      "--require-rollback",
    ],
    { cwd: desktopDirectory },
  );
  const receipt = JSON.parse(
    await fs.readFile(
      path.join(evidence, "update-verification-linux-x64.json"),
      "utf8",
    ),
  );
  assert.deepEqual(receipt.signer_ids, ["test-release"]);
  assert.equal(receipt.version, "1.0.1");
});
