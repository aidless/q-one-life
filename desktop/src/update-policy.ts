import { createPublicKey, verify as verifySignature } from "node:crypto";

export type UpdateChannel = "beta" | "stable";
export type UpdatePlatform = "darwin" | "linux" | "win32";
export type UpdateArch = "arm64" | "x64";

export interface ReleaseFile {
  name: string;
  url: string;
  bytes: number;
  sha256: string;
  sha512: string;
}

export interface UpdateArtifact extends ReleaseFile {
  platform: UpdatePlatform;
  arch: UpdateArch;
  kind: "appimage" | "dmg" | "nsis" | "zip";
  rollback: boolean;
}

export interface UpdateMetadata extends ReleaseFile {
  target: `${UpdatePlatform}-${UpdateArch}`;
}

export interface UpdatePayload {
  schema: "q-one-update-manifest-v1";
  channel: UpdateChannel;
  version: string;
  published_at: string;
  minimum_version?: string;
  metadata: UpdateMetadata;
  artifacts: UpdateArtifact[];
}

export interface UpdateSignature {
  key_id: string;
  signature: string;
}

export interface SignedUpdateManifest {
  payload: UpdatePayload;
  signatures: UpdateSignature[];
}

export interface VerifyUpdateOptions {
  currentVersion: string;
  channel: UpdateChannel;
  platform: UpdatePlatform;
  arch: UpdateArch;
  trustedKeys: Readonly<Record<string, string>>;
  allowedHosts?: readonly string[];
  minimumSignatures?: number;
}

export interface VerifiedUpdate {
  channel: UpdateChannel;
  version: string;
  metadata: UpdateMetadata;
  artifact: UpdateArtifact;
  rollback?: UpdateArtifact;
  signerIds: string[];
}

export const DEFAULT_ALLOWED_HOSTS = [
  "aidless.github.io",
  "github.com",
  "objects.githubusercontent.com",
  "release-assets.githubusercontent.com",
] as const;

export function linuxUpdateRequiresManualInstall(
  packageType: string | undefined,
  appImagePath: string | undefined,
): boolean {
  // electron-builder writes one package-type file into the shared linux-unpacked
  // directory. A subsequent deb build can therefore mark an AppImage payload as
  // deb; APPIMAGE is present only when the running artifact is an AppImage.
  return packageType?.trim().toLowerCase() === "deb" && !appImagePath?.trim();
}

const SAFE_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/;
const KEY_ID = /^[A-Za-z0-9._-]{1,80}$/;
const SHA256 = /^[a-f0-9]{64}$/;
const SHA512 = /^[a-f0-9]{128}$/;
const SEMVER =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z.-]+)?$/;

function plainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function semverParts(version: string): {
  core: [number, number, number];
  prerelease: string[];
} {
  const match = SEMVER.exec(version);
  if (!match) throw new Error(`invalid update version: ${version}`);
  return {
    core: [Number(match[1]), Number(match[2]), Number(match[3])],
    prerelease: match[4]?.split(".") ?? [],
  };
}

function comparePrerelease(left: string[], right: string[]): number {
  if (!left.length && !right.length) return 0;
  if (!left.length) return 1;
  if (!right.length) return -1;
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const a = left[index];
    const b = right[index];
    if (a === undefined) return -1;
    if (b === undefined) return 1;
    if (a === b) continue;
    const aNumber = /^\d+$/.test(a);
    const bNumber = /^\d+$/.test(b);
    if (aNumber && bNumber) return Number(a) < Number(b) ? -1 : 1;
    if (aNumber !== bNumber) return aNumber ? -1 : 1;
    return a.localeCompare(b, "en");
  }
  return 0;
}

export function compareVersions(left: string, right: string): number {
  const a = semverParts(left);
  const b = semverParts(right);
  for (let index = 0; index < 3; index += 1) {
    if (a.core[index] !== b.core[index]) {
      return a.core[index] < b.core[index] ? -1 : 1;
    }
  }
  return comparePrerelease(a.prerelease, b.prerelease);
}

export function channelForVersion(version: string): UpdateChannel {
  return semverParts(version).prerelease.length ? "beta" : "stable";
}

export function canonicalJson(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string" || typeof value === "boolean") {
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("canonical JSON rejects non-finite numbers");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  }
  if (!plainObject(value)) {
    throw new Error("canonical JSON only accepts JSON values");
  }
  return `{${Object.keys(value)
    .filter((key) => value[key] !== undefined)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
    .join(",")}}`;
}

function signedMessage(payload: unknown): Buffer {
  return Buffer.from(canonicalJson(payload), "utf8");
}

function decodeBase64(value: string, label: string): Buffer {
  if (!value || !/^[A-Za-z0-9+/]+={0,2}$/.test(value) || value.length % 4 !== 0) {
    throw new Error(`${label} is not strict base64`);
  }
  const decoded = Buffer.from(value, "base64");
  if (decoded.toString("base64") !== value) {
    throw new Error(`${label} is not canonical base64`);
  }
  return decoded;
}

function trustedPublicKey(encoded: string) {
  const key = createPublicKey({
    key: Buffer.from(encoded, "base64"),
    format: "der",
    type: "spki",
  });
  if (key.asymmetricKeyType !== "ed25519") {
    throw new Error("trusted update key must be Ed25519");
  }
  return key;
}

function validUrl(
  value: unknown,
  allowedHosts: readonly string[],
): value is string {
  if (typeof value !== "string") return false;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  return (
    url.protocol === "https:" &&
    `${url.protocol}//${url.host}${url.pathname}${url.search}${url.hash}` ===
      url.href &&
    !url.port &&
    !url.search &&
    !url.hash &&
    allowedHosts.includes(url.hostname.toLowerCase()) &&
    !url.pathname.split("/").includes("..")
  );
}

function validFile(
  value: unknown,
  allowedHosts: readonly string[],
): value is ReleaseFile {
  if (!plainObject(value)) return false;
  return (
    typeof value.name === "string" &&
    SAFE_NAME.test(value.name) &&
    validUrl(value.url, allowedHosts) &&
    Number.isSafeInteger(value.bytes) &&
    Number(value.bytes) > 0 &&
    Number(value.bytes) <= 8 * 1024 * 1024 * 1024 &&
    typeof value.sha256 === "string" &&
    SHA256.test(value.sha256) &&
    typeof value.sha512 === "string" &&
    SHA512.test(value.sha512)
  );
}

function validArtifact(
  value: unknown,
  allowedHosts: readonly string[],
): value is UpdateArtifact {
  if (!validFile(value, allowedHosts) || !plainObject(value)) return false;
  return (
    ["linux", "darwin", "win32"].includes(String(value.platform)) &&
    ["x64", "arm64"].includes(String(value.arch)) &&
    ["appimage", "dmg", "nsis", "zip"].includes(String(value.kind)) &&
    typeof value.rollback === "boolean"
  );
}

function expectedMetadataName(
  channel: UpdateChannel,
  platform: UpdatePlatform,
): string {
  if (platform === "linux") {
    return channel === "stable" ? "latest-linux.yml" : "beta-linux.yml";
  }
  if (platform === "darwin") {
    return channel === "stable" ? "latest-mac.yml" : "beta-mac.yml";
  }
  return channel === "stable" ? "latest.yml" : "beta.yml";
}

function artifactMatches(
  artifact: UpdateArtifact,
  platform: UpdatePlatform,
  arch: UpdateArch,
): boolean {
  if (artifact.platform !== platform || artifact.arch !== arch) return false;
  if (platform === "linux") return artifact.kind === "appimage";
  // electron-updater installs the ZIP on macOS. The DMG remains a separate
  // first-install artifact and must not be selected as an updater payload.
  if (platform === "darwin") return artifact.kind === "zip";
  return artifact.kind === "nsis";
}

export function verifyUpdateManifest(
  manifest: unknown,
  options: VerifyUpdateOptions,
): VerifiedUpdate {
  if (!plainObject(manifest) || !plainObject(manifest.payload)) {
    throw new Error("update manifest shape is invalid");
  }
  const payload = manifest.payload;
  if (payload.schema !== "q-one-update-manifest-v1") {
    throw new Error("unsupported update manifest schema");
  }
  if (payload.channel !== options.channel) {
    throw new Error("update manifest channel does not match this installation");
  }
  if (typeof payload.version !== "string") {
    throw new Error("update manifest version is missing");
  }
  const incomingChannel = channelForVersion(payload.version);
  if (incomingChannel !== options.channel) {
    throw new Error("update version does not match its declared channel");
  }
  if (compareVersions(payload.version, options.currentVersion) <= 0) {
    throw new Error("update manifest is not newer than the installed version");
  }
  if (typeof payload.published_at !== "string" || !Number.isFinite(Date.parse(payload.published_at))) {
    throw new Error("update publication time is invalid");
  }
  if (
    payload.minimum_version !== undefined &&
    (typeof payload.minimum_version !== "string" ||
      compareVersions(options.currentVersion, payload.minimum_version) < 0)
  ) {
    throw new Error("installed version is below the update minimum version");
  }
  const allowedHosts = options.allowedHosts ?? DEFAULT_ALLOWED_HOSTS;
  if (!validFile(payload.metadata, allowedHosts) || !plainObject(payload.metadata)) {
    throw new Error("update metadata file is invalid");
  }
  if (
    payload.metadata.name !==
    expectedMetadataName(options.channel, options.platform)
  ) {
    throw new Error("update metadata filename does not match the target");
  }
  if (payload.metadata.target !== `${options.platform}-${options.arch}`) {
    throw new Error("update metadata target does not match this installation");
  }
  if (!Array.isArray(payload.artifacts) || !payload.artifacts.length) {
    throw new Error("update artifacts are missing");
  }
  const artifacts = payload.artifacts;
  if (artifacts.length > 20 || !artifacts.every((item) => validArtifact(item, allowedHosts))) {
    throw new Error("update artifact list is invalid");
  }
  const matching = artifacts.filter(
    (artifact) =>
      !artifact.rollback &&
      artifactMatches(artifact, options.platform, options.arch),
  );
  if (matching.length !== 1) {
    throw new Error("update manifest must identify exactly one install artifact");
  }
  const rollbacks = artifacts.filter(
    (artifact) =>
      artifact.rollback &&
      artifactMatches(artifact, options.platform, options.arch),
  );
  if (rollbacks.length > 1) {
    throw new Error("update manifest must identify at most one rollback artifact");
  }
  const rollback = rollbacks[0];

  if (!Array.isArray(manifest.signatures) || !manifest.signatures.length) {
    throw new Error("update manifest is unsigned");
  }
  const message = signedMessage(payload);
  const signerIds = new Set<string>();
  let validSignatures = 0;
  for (const signature of manifest.signatures) {
    if (
      !plainObject(signature) ||
      typeof signature.key_id !== "string" ||
      !KEY_ID.test(signature.key_id) ||
      typeof signature.signature !== "string"
    ) {
      continue;
    }
    const encodedKey = options.trustedKeys[signature.key_id];
    if (!encodedKey) continue;
    try {
      const key = trustedPublicKey(encodedKey);
      const bytes = decodeBase64(signature.signature, "manifest signature");
      if (verifySignature(null, message, key, bytes)) {
        validSignatures += 1;
        signerIds.add(signature.key_id);
      }
    } catch {
      // A malformed or untrusted signature never weakens a valid one.
    }
  }
  const minimum = options.minimumSignatures ?? 1;
  if (!Number.isSafeInteger(minimum) || minimum < 1) {
    throw new Error("minimum signature count is invalid");
  }
  if (validSignatures < minimum) {
    throw new Error("update manifest lacks a trusted signature");
  }
  const channel = payload.channel as UpdateChannel;
  const metadata = payload.metadata as unknown as UpdateMetadata;
  const artifact = matching[0] as UpdateArtifact;
  const rollbackArtifact = rollback as UpdateArtifact | undefined;
  return {
    channel,
    version: String(payload.version),
    metadata,
    artifact,
    ...(rollbackArtifact ? { rollback: rollbackArtifact } : {}),
    signerIds: [...signerIds],
  };
}
