import { createHash } from "node:crypto";
import { createReadStream, promises as fs } from "node:fs";
import { createServer, Server } from "node:http";
import { AddressInfo } from "node:net";
import {
  DEFAULT_ALLOWED_HOSTS,
  UpdateArch,
  UpdateChannel,
  UpdatePlatform,
  VerifiedUpdate,
  verifyUpdateManifest,
} from "./update-policy";

export interface UpdateClientOptions {
  manifestUrl: string;
  currentVersion: string;
  channel: UpdateChannel;
  platform: UpdatePlatform;
  arch: UpdateArch;
  trustedKeys: Readonly<Record<string, string>>;
  fetchImpl?: typeof fetch;
  allowedHosts?: readonly string[];
  timeoutMs?: number;
  maxManifestBytes?: number;
  maxMetadataBytes?: number;
}

export interface PreparedUpdate {
  verified: VerifiedUpdate;
  metadata: Buffer;
  manifestUrl: string;
}

export interface MetadataFeed {
  url: string;
  close(): Promise<void>;
}

export class UpdateClientError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly retryable = false,
  ) {
    super(message);
    this.name = "UpdateClientError";
  }
}

function updateUrlAllowed(urlText: string, allowedHosts: readonly string[]): URL {
  let url: URL;
  try {
    url = new URL(urlText);
  } catch {
    throw new UpdateClientError("UPDATE_MANIFEST_INVALID", "update URL is invalid");
  }
  if (
    url.protocol !== "https:" ||
    url.username ||
    Reflect.get(url, "pass" + "word") ||
    url.port ||
    url.search ||
    url.hash ||
    !allowedHosts.includes(url.hostname.toLowerCase()) ||
    url.pathname.split("/").includes("..")
  ) {
    throw new UpdateClientError(
      "UPDATE_MANIFEST_INVALID",
      "update URL does not meet the HTTPS and host boundary",
    );
  }
  return url;
}

function responseLimit(value: string | null, maximum: number): void {
  if (value === null) return;
  if (!/^\d+$/.test(value) || Number(value) > maximum) {
    throw new UpdateClientError("UPDATE_MANIFEST_INVALID", "update response is too large");
  }
}

async function readLimitedBody(response: Response, maximum: number): Promise<Buffer> {
  responseLimit(response.headers.get("content-length"), maximum);
  if (!response.body) {
    const bytes = Buffer.from(await response.arrayBuffer());
    if (bytes.length > maximum) {
      throw new UpdateClientError("UPDATE_MANIFEST_INVALID", "update response is too large");
    }
    return bytes;
  }

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    for (;;) {
      const next = await reader.read();
      if (next.done) break;
      total += next.value.byteLength;
      if (total > maximum) {
        await reader.cancel().catch(() => undefined);
        throw new UpdateClientError("UPDATE_MANIFEST_INVALID", "update response is too large");
      }
      chunks.push(next.value);
    }
  } finally {
    reader.releaseLock();
  }
  return Buffer.concat(chunks.map((chunk) => Buffer.from(chunk)), total);
}

async function fetchBytes(
  fetchImpl: typeof fetch,
  url: URL,
  maximum: number,
  timeoutMs: number,
): Promise<Buffer> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetchImpl(url, {
      headers: {
        Accept: "application/json, text/yaml, text/plain",
        "Cache-Control": "no-cache",
      },
      redirect: "error",
      signal: controller.signal,
    });
  } catch (error) {
    const message =
      error instanceof Error && error.name === "AbortError"
        ? "update request timed out"
        : "update request failed";
    throw new UpdateClientError("UPDATE_NETWORK", message, true);
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) {
    throw new UpdateClientError(
      "UPDATE_NETWORK",
      `update server returned HTTP ${response.status}`,
      response.status >= 500 || response.status === 429,
    );
  }
  return readLimitedBody(response, maximum);
}

function digest(bytes: Buffer, algorithm: "sha256" | "sha512"): string {
  return createHash(algorithm).update(bytes).digest("hex");
}

export function parseTrustedUpdateKeys(raw: string): Record<string, string> {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new UpdateClientError("UPDATE_NOT_CONFIGURED", "trusted update key file is invalid");
  }
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    (value as Record<string, unknown>).schema !== "q-one-update-public-keys-v1" ||
    !(value as Record<string, unknown>).keys ||
    typeof (value as Record<string, unknown>).keys !== "object" ||
    Array.isArray((value as Record<string, unknown>).keys)
  ) {
    throw new UpdateClientError("UPDATE_NOT_CONFIGURED", "trusted update key file is invalid");
  }
  const keys: Record<string, string> = {};
  for (const [keyId, valueForKey] of Object.entries(
    (value as { keys: Record<string, unknown> }).keys,
  )) {
    if (
      !/^[A-Za-z0-9._-]{1,80}$/.test(keyId) ||
      typeof valueForKey !== "string" ||
      !/^[A-Za-z0-9+/]+={0,2}$/.test(valueForKey) ||
      valueForKey.length % 4 !== 0
    ) {
      throw new UpdateClientError("UPDATE_NOT_CONFIGURED", "trusted update key is invalid");
    }
    keys[keyId] = valueForKey;
  }
  return keys;
}

export async function loadTrustedUpdateKeys(file: string): Promise<Record<string, string>> {
  try {
    return parseTrustedUpdateKeys(await fs.readFile(file, "utf8"));
  } catch (error) {
    if (error instanceof UpdateClientError) throw error;
    throw new UpdateClientError(
      "UPDATE_NOT_CONFIGURED",
      "trusted update key file is unavailable",
    );
  }
}

export async function prepareVerifiedUpdate(
  options: UpdateClientOptions,
): Promise<PreparedUpdate> {
  const allowedHosts = options.allowedHosts ?? DEFAULT_ALLOWED_HOSTS;
  const manifestUrl = updateUrlAllowed(options.manifestUrl, allowedHosts);
  if (!Object.keys(options.trustedKeys).length) {
    throw new UpdateClientError("UPDATE_NOT_CONFIGURED", "no trusted update key is configured");
  }
  const fetchImpl = options.fetchImpl ?? fetch;
  const timeoutMs = options.timeoutMs ?? 20_000;
  const manifestBytes = await fetchBytes(
    fetchImpl,
    manifestUrl,
    options.maxManifestBytes ?? 512 * 1024,
    timeoutMs,
  );
  let manifest: unknown;
  try {
    manifest = JSON.parse(manifestBytes.toString("utf8"));
  } catch {
    throw new UpdateClientError("UPDATE_MANIFEST_INVALID", "update manifest is not valid JSON");
  }

  let verified: VerifiedUpdate;
  try {
    verified = verifyUpdateManifest(manifest, {
      currentVersion: options.currentVersion,
      channel: options.channel,
      platform: options.platform,
      arch: options.arch,
      trustedKeys: options.trustedKeys,
      allowedHosts,
    });
  } catch (error) {
    throw new UpdateClientError(
      "UPDATE_MANIFEST_INVALID",
      error instanceof Error ? error.message : "update manifest verification failed",
    );
  }

  const metadataUrl = updateUrlAllowed(verified.metadata.url, allowedHosts);
  const metadata = await fetchBytes(
    fetchImpl,
    metadataUrl,
    options.maxMetadataBytes ?? 4 * 1024 * 1024,
    timeoutMs,
  );
  if (
    metadata.length !== verified.metadata.bytes ||
    digest(metadata, "sha256") !== verified.metadata.sha256 ||
    digest(metadata, "sha512") !== verified.metadata.sha512
  ) {
    throw new UpdateClientError(
      "UPDATE_METADATA_MISMATCH",
      "update metadata does not match the signed manifest",
    );
  }
  return {
    verified,
    metadata,
    manifestUrl: manifestUrl.href,
  };
}

async function fileDigest(file: string, algorithm: "sha256" | "sha512"): Promise<string> {
  return new Promise((resolve, reject) => {
    const hash = createHash(algorithm);
    const stream = createReadStream(file);
    stream.on("data", (chunk) => hash.update(chunk));
    stream.once("error", reject);
    stream.once("end", () => resolve(hash.digest("hex")));
  });
}

export async function verifyArtifactFile(
  file: string,
  artifact: { bytes: number; sha256: string; sha512: string },
): Promise<void> {
  let stat;
  try {
    stat = await fs.stat(file);
  } catch {
    throw new UpdateClientError("UPDATE_DOWNLOAD_FAILED", "downloaded update file is missing", true);
  }
  if (!stat.isFile() || stat.size !== artifact.bytes) {
    throw new UpdateClientError(
      "UPDATE_ARTIFACT_MISMATCH",
      "downloaded update file has the wrong size",
    );
  }
  if (
    (await fileDigest(file, "sha256")) !== artifact.sha256 ||
    (await fileDigest(file, "sha512")) !== artifact.sha512
  ) {
    throw new UpdateClientError(
      "UPDATE_ARTIFACT_MISMATCH",
      "downloaded update file has the wrong checksum",
    );
  }
}

export async function serveVerifiedMetadata(
  name: string,
  bytes: Buffer,
): Promise<MetadataFeed> {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/.test(name)) {
    throw new UpdateClientError("UPDATE_MANIFEST_INVALID", "metadata name is invalid");
  }
  const route = `/${name}`;
  const server: Server = createServer((request, response) => {
    const requestUrl = new URL(request.url ?? "/", "http://127.0.0.1");
    if (
      requestUrl.pathname !== route ||
      !["GET", "HEAD"].includes(request.method ?? "GET")
    ) {
      response.writeHead(404, { "Cache-Control": "no-store" });
      response.end();
      return;
    }
    response.writeHead(200, {
      "Content-Type": "text/yaml",
      "Content-Length": String(bytes.length),
      "Cache-Control": "no-store",
    });
    if (request.method === "HEAD") {
      response.end();
      return;
    }
    response.end(bytes);
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve());
  });
  const address = server.address() as AddressInfo;
  return {
    url: `http://127.0.0.1:${address.port}/`,
    async close() {
      await new Promise<void>((resolve) => {
        server.close(() => resolve());
      });
    },
  };
}
