import { createHash } from "node:crypto";
import { createReadStream, promises as fs } from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const desktopDirectory = path.resolve(scriptDirectory, "..");
const { parseTrustedUpdateKeys } = require(
  path.join(desktopDirectory, "dist", "update-client.js"),
);
const {
  channelForVersion,
  verifyUpdateManifest,
} = require(path.join(desktopDirectory, "dist", "update-policy.js"));

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function fail(message) {
  console.error(`QONE_RELEASE_VERIFY_FAILED ${message}`);
  process.exit(1);
}

async function digest(file, algorithm) {
  const hash = createHash(algorithm);
  for await (const chunk of createReadStream(file)) hash.update(chunk);
  return hash.digest("hex");
}

async function verifiedFile(entry, file) {
  const stat = await fs.stat(file).catch(() => {
    throw new Error(`signed file is missing: ${file}`);
  });
  if (!stat.isFile()) throw new Error(`signed path is not a file: ${file}`);
  if (stat.size !== entry.bytes) {
    throw new Error(
      `size mismatch for ${entry.name}: expected ${entry.bytes}, got ${stat.size}`,
    );
  }
  const sha256 = await digest(file, "sha256");
  const sha512 = await digest(file, "sha512");
  if (sha256 !== entry.sha256) {
    throw new Error(`SHA-256 mismatch for ${entry.name}`);
  }
  if (sha512 !== entry.sha512) {
    throw new Error(`SHA-512 mismatch for ${entry.name}`);
  }
  return { name: entry.name, bytes: stat.size, sha256, sha512 };
}

async function checksumEntries(file) {
  const text = await fs.readFile(file, "utf8");
  const entries = new Map();
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    const match = /^([a-f0-9]{64})  (.+)$/.exec(line);
    if (!match) throw new Error(`invalid checksum line in ${file}`);
    if (entries.has(match[2])) {
      throw new Error(`duplicate checksum entry for ${match[2]}`);
    }
    entries.set(match[2], match[1]);
  }
  return entries;
}

async function main() {
  if (hasFlag("--help")) {
    console.log(
      [
        "Usage: node scripts/verify-release.mjs --from-version VERSION [options]",
        "",
        "Required:",
        "  --from-version VERSION   Currently installed version",
        "",
        "Options:",
        "  --release-dir DIR        Release root (default: desktop/release)",
        "  --manifest FILE          Signed update manifest",
        "  --public-keys FILE       Trusted public-key JSON",
        "  --platform PLATFORM      linux, darwin, or win32",
        "  --arch ARCH              x64 or arm64",
        "  --channel CHANNEL        stable or beta; defaults from version",
        "  --require-rollback       Fail unless a signed rollback artifact exists",
      ].join("\n"),
    );
    return;
  }
  const releaseDirectory = path.resolve(
    argument("--release-dir", path.join(desktopDirectory, "release")),
  );
  const platform = argument("--platform", process.platform);
  const arch = argument(
    "--arch",
    process.arch === "arm64" ? "arm64" : "x64",
  );
  const fromVersion = argument("--from-version");
  if (!fromVersion) fail("--from-version is required");
  if (!["linux", "darwin", "win32"].includes(platform)) {
    fail(`unsupported platform ${platform}`);
  }
  if (!["x64", "arm64"].includes(arch)) fail(`unsupported architecture ${arch}`);

  const publicKeyFile = path.resolve(
    argument(
      "--public-keys",
      path.join(desktopDirectory, "update-public-keys.json"),
    ),
  );
  const trustedKeys = parseTrustedUpdateKeys(
    await fs.readFile(publicKeyFile, "utf8"),
  );
  if (!Object.keys(trustedKeys).length) {
    fail("trusted update key file is empty");
  }

  const manifestFile = path.resolve(
    argument(
      "--manifest",
      path.join(releaseDirectory, "updates", "stable", "manifest.json"),
    ),
  );
  const manifestBytes = await fs.readFile(manifestFile, "utf8");
  let signedManifest;
  try {
    signedManifest = JSON.parse(manifestBytes);
  } catch {
    fail("update manifest is not valid JSON");
  }
  const version = signedManifest?.payload?.version;
  if (typeof version !== "string") fail("update manifest version is missing");
  const channel = argument("--channel", channelForVersion(version));
  const verified = verifyUpdateManifest(signedManifest, {
    currentVersion: fromVersion,
    channel,
    platform,
    arch,
    trustedKeys,
  });

  const manifestDirectory = path.dirname(manifestFile);
  const metadataFile = path.join(manifestDirectory, verified.metadata.name);
  const artifactFile = path.join(releaseDirectory, verified.artifact.name);
  const files = [
    await verifiedFile(verified.metadata, metadataFile),
    await verifiedFile(verified.artifact, artifactFile),
  ];
  if (verified.rollback) {
    files.push(
      await verifiedFile(
        verified.rollback,
        path.join(releaseDirectory, verified.rollback.name),
      ),
    );
  } else if (hasFlag("--require-rollback")) {
    fail("signed manifest does not contain a rollback artifact");
  }

  const releaseChecksums = path.join(
    releaseDirectory,
    "evidence",
    "SHA256SUMS.txt",
  );
  const releaseChecksumEntries = await checksumEntries(releaseChecksums).catch(
    (error) => {
      throw new Error(
        `release checksum manifest is unavailable: ${error.message}`,
      );
    },
  );
  for (const file of files.filter((item) => item !== files[0])) {
    const expected = releaseChecksumEntries.get(file.name);
    if (!expected) {
      throw new Error(`release checksum manifest omits ${file.name}`);
    }
    if (expected !== file.sha256) {
      throw new Error(`release checksum manifest disagrees for ${file.name}`);
    }
  }

  const updateChecksumPath = path.join(manifestDirectory, "SHA256SUMS.txt");
  const updateFiles = [
    {
      name: path.basename(manifestFile),
      sha256: await digest(manifestFile, "sha256"),
    },
    ...files,
  ];
  await fs.writeFile(
    updateChecksumPath,
    `${updateFiles.map((file) => `${file.sha256}  ${file.name}`).join("\n")}\n`,
    { mode: 0o644 },
  );

  const evidenceDirectory = path.join(releaseDirectory, "evidence");
  await fs.mkdir(evidenceDirectory, { recursive: true, mode: 0o755 });
  const receipt = {
    schema: "q-one-update-verification-v1",
    generated_at: new Date().toISOString(),
    platform,
    arch,
    channel,
    from_version: fromVersion,
    version: verified.version,
    signer_ids: verified.signerIds,
    manifest: {
      name: path.basename(manifestFile),
      sha256: await digest(manifestFile, "sha256"),
    },
    files,
    rollback_present: Boolean(verified.rollback),
  };
  const receiptFile = path.join(
    evidenceDirectory,
    `update-verification-${platform}-${arch}.json`,
  );
  await fs.writeFile(receiptFile, `${JSON.stringify(receipt, null, 2)}\n`, {
    mode: 0o644,
  });

  console.log(
    `QONE_RELEASE_VERIFY_OK ${JSON.stringify({
      platform,
      arch,
      channel,
      version: verified.version,
      signers: verified.signerIds,
      rollback: Boolean(verified.rollback),
      receipt: receiptFile,
    })}`,
  );
}

main().catch((error) =>
  fail(error instanceof Error ? error.message : String(error)),
);
