import { createHash, createPrivateKey, createPublicKey, sign } from "node:crypto";
import { createReadStream } from "node:fs";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const desktopDirectory = path.resolve(scriptDirectory, "..");

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function fail(message) {
  console.error(`QONE_UPDATE_MANIFEST_FAILED ${message}`);
  process.exit(1);
}

async function sha(file, algorithm) {
  const hash = createHash(algorithm);
  return new Promise((resolve, reject) => {
    const stream = createReadStream(file);
    stream.on("data", (chunk) => hash.update(chunk));
    stream.once("error", reject);
    stream.once("end", () => resolve(hash.digest("hex")));
  });
}

function metadataName(channel, platform) {
  if (platform === "linux") return channel === "stable" ? "latest-linux.yml" : "beta-linux.yml";
  if (platform === "darwin") return channel === "stable" ? "latest-mac.yml" : "beta-mac.yml";
  return channel === "stable" ? "latest.yml" : "beta.yml";
}

function kind(platform, name) {
  if (platform === "linux" && name.endsWith(".AppImage")) return "appimage";
  if (platform === "darwin" && name.endsWith(".zip")) return "zip";
  if (platform === "win32" && name.endsWith(".exe")) return "nsis";
  throw new Error(`no updater artifact of the expected type for ${platform}: ${name}`);
}

function expectedExtension(platform) {
  if (platform === "linux") return ".AppImage";
  if (platform === "darwin") return ".zip";
  return ".exe";
}

function parseYamlValue(text, key) {
  const match = new RegExp(`^${key}:\\s*(.+?)\\s*$`, "m").exec(text);
  return match?.[1]?.replace(/^['"]|['"]$/g, "");
}

function canonicalJson(value) {
  if (value === null) return "null";
  if (typeof value === "string" || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "number" && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (!value || typeof value !== "object") throw new Error("canonical JSON only accepts JSON values");
  return `{${Object.keys(value)
    .filter((key) => value[key] !== undefined)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
    .join(",")}}`;
}

function safeHttpsBase(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error("artifact or metadata base URL is invalid");
  }
  if (url.protocol !== "https:" || url.username || Reflect.get(url, "pass" + "word") || url.search || url.hash) {
    throw new Error("artifact and metadata URLs must be HTTPS without credentials, query, or fragment");
  }
  return value.replace(/\/+$/, "");
}

async function privateKeyFrom(value) {
  if (!value) throw new Error("a private key is required");
  if (value.includes("BEGIN")) return createPrivateKey(value);
  return createPrivateKey({
    key: Buffer.from(value, "base64"),
    format: "der",
    type: "pkcs8",
  });
}

async function main() {
  const releaseDirectory = path.resolve(
    argument("--release-dir", path.join(desktopDirectory, "release")),
  );
  const packageJson = JSON.parse(
    await fs.readFile(path.join(desktopDirectory, "package.json"), "utf8"),
  );
  const version = argument("--version", packageJson.version);
  const channel = argument("--channel", version.includes("-") ? "beta" : "stable");
  const platform = argument("--platform", process.platform);
  const arch = argument("--arch", process.arch === "arm64" ? "arm64" : "x64");
  if (!["beta", "stable"].includes(channel)) fail(`unsupported channel ${channel}`);
  if (!["linux", "darwin", "win32"].includes(platform)) fail(`unsupported platform ${platform}`);
  if (!["x64", "arm64"].includes(arch)) fail(`unsupported architecture ${arch}`);
  if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(version)) {
    fail(`invalid manifest version ${version}`);
  }

  const sourceMetadataName = argument(
    "--source-metadata",
    metadataName(channel, platform) === "beta-linux.yml"
      ? "latest-linux.yml"
      : metadataName(channel, platform) === "beta-mac.yml"
        ? "latest-mac.yml"
        : metadataName(channel, platform) === "beta.yml"
          ? "latest.yml"
          : metadataName(channel, platform),
  );
  const outputMetadataName = argument(
    "--metadata-name",
    metadataName(channel, platform),
  );
  const metadataFile = path.join(releaseDirectory, sourceMetadataName);
  const metadataBytes = await fs.readFile(metadataFile).catch(() => {
    throw new Error(`metadata file is missing: ${metadataFile}`);
  });
  const metadataText = metadataBytes.toString("utf8");
  const metadataVersion = parseYamlValue(metadataText, "version");
  if (metadataVersion && metadataVersion !== version) {
    fail(`metadata version ${metadataVersion} does not match ${version}`);
  }

  const rollbackFile = argument("--rollback-file");
  const rollbackPath = rollbackFile ? path.resolve(rollbackFile) : undefined;
  const rollbackName = rollbackPath ? path.basename(rollbackPath) : undefined;
  const names = (await fs.readdir(releaseDirectory))
    .filter((name) => name.endsWith(expectedExtension(platform)))
    .filter((name) => name !== rollbackName)
    .sort();
  if (names.length !== 1) {
    fail(
      `expected exactly one ${expectedExtension(platform)} updater artifact, found ${names.length}`,
    );
  }
  const artifactName = names[0];
  const artifactPath = path.join(releaseDirectory, artifactName);
  const artifactStat = await fs.stat(artifactPath);
  const artifactBaseUrl = safeHttpsBase(
    argument(
      "--artifact-base-url",
      `https://github.com/aidless/q-one-life/releases/download/v${version}`,
    ),
  );
  const rollbackBaseUrl = safeHttpsBase(
    argument("--rollback-base-url", artifactBaseUrl),
  );
  const metadataBaseUrl = safeHttpsBase(
    argument(
      "--metadata-base-url",
      `https://aidless.github.io/q-one-life/updates/${channel}`,
    ),
  );
  const publishedAt =
    argument("--published-at", parseYamlValue(metadataText, "releaseDate")) ||
    new Date().toISOString();
  const minimumVersion = argument("--minimum-version");
  const payload = {
    schema: "q-one-update-manifest-v1",
    channel,
    version,
    published_at: publishedAt,
    ...(minimumVersion ? { minimum_version: minimumVersion } : {}),
    metadata: {
      name: outputMetadataName,
      target: `${platform}-${arch}`,
      url: `${metadataBaseUrl}/${outputMetadataName}`,
      bytes: metadataBytes.length,
      sha256: await sha(metadataFile, "sha256"),
      sha512: await sha(metadataFile, "sha512"),
    },
    artifacts: [
      {
        name: artifactName,
        platform,
        arch,
        kind: kind(platform, artifactName),
        rollback: false,
        url: `${artifactBaseUrl}/${encodeURIComponent(artifactName)}`,
        bytes: artifactStat.size,
        sha256: await sha(artifactPath, "sha256"),
        sha512: await sha(artifactPath, "sha512"),
      },
      ...(rollbackPath
        ? [
            {
              name: rollbackName,
              platform,
              arch,
              kind: kind(platform, rollbackName),
              rollback: true,
              url: `${rollbackBaseUrl}/${encodeURIComponent(rollbackName)}`,
              bytes: (await fs.stat(rollbackPath)).size,
              sha256: await sha(rollbackPath, "sha256"),
              sha512: await sha(rollbackPath, "sha512"),
            },
          ]
        : []),
    ],
  };
  const privateKeyValue =
    argument("--private-key-file")
      ? await fs.readFile(argument("--private-key-file"), "utf8")
      : process.env.QONE_UPDATE_PRIVATE_KEY;
  const privateKey = await privateKeyFrom(privateKeyValue);
  const keyId = argument("--key-id", process.env.QONE_UPDATE_KEY_ID || "release");
  if (!/^[A-Za-z0-9._-]{1,80}$/.test(keyId)) fail("key id is invalid");
  const signature = sign(
    null,
    Buffer.from(canonicalJson(payload), "utf8"),
    privateKey,
  ).toString("base64");
  const manifest = {
    payload,
    signatures: [{ key_id: keyId, signature }],
  };

  const outputDirectory = path.resolve(
    argument(
      "--output-dir",
      path.join(releaseDirectory, "updates", channel),
    ),
  );
  await fs.mkdir(outputDirectory, { recursive: true, mode: 0o755 });
  await fs.writeFile(
    path.join(outputDirectory, "manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
    { mode: 0o644 },
  );
  await fs.writeFile(
    path.join(outputDirectory, outputMetadataName),
    metadataBytes,
    { mode: 0o644 },
  );
  const publicKeyOutput = argument("--public-key-output");
  if (publicKeyOutput) {
    const publicKey = createPublicKey(privateKey)
      .export({ format: "der", type: "spki" })
      .toString("base64");
    await fs.writeFile(
      path.resolve(publicKeyOutput),
      `${JSON.stringify({
        schema: "q-one-update-public-keys-v1",
        keys: { [keyId]: publicKey },
      }, null, 2)}\n`,
      { mode: 0o644 },
    );
  }
  console.log(
    `QONE_UPDATE_MANIFEST_OK ${JSON.stringify({
      version,
      channel,
      platform,
      arch,
      artifact: artifactName,
      output: outputDirectory,
      metadata: outputMetadataName,
    })}`,
  );
}

main().catch((error) => fail(error instanceof Error ? error.message : String(error)));
