import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";

export const QWEN_MODEL = {
  repository: "Qwen/Qwen3-0.6B-GGUF",
  revision: "23749fefcc72300e3a2ad315e1317431b06b590a",
  filename: "Qwen3-0.6B-Q8_0.gguf",
  bytes: 639_446_688,
  sha256: "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031",
  license: "Apache-2.0",
  url:
    "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/" +
    "23749fefcc72300e3a2ad315e1317431b06b590a/Qwen3-0.6B-Q8_0.gguf",
  fallback_url:
    "https://modelscope.cn/models/Qwen/Qwen3-0.6B-GGUF/resolve/" +
    "6abe20cd0aed577f4d0b267935868ecae190aee9/Qwen3-0.6B-Q8_0.gguf",
} as const;

export const DEFAULT_ALLOWED_HOSTS = [
  "huggingface.co",
  "cdn-lfs.hf.co",
  "cdn-lfs-us-1.hf.co",
  "cdn-lfs-eu-1.hf.co",
  "us.aws.cdn.hf.co",
  "modelscope.cn",
  "cdn-lfs-cn-1.modelscope.cn",
];

export type ModelDownloadPhase =
  | "starting"
  | "downloading"
  | "verifying"
  | "installed";

export interface ModelDownloadProgress {
  phase: ModelDownloadPhase;
  received: number;
  total: number;
}

export type ModelFetch = (
  input: string | URL,
  init?: RequestInit,
) => Promise<Response>;

export interface VerifiedDownloadOptions {
  url: string;
  expectedBytes: number;
  expectedSha256: string;
  destination: string;
  signal?: AbortSignal;
  fetchImpl?: ModelFetch;
  allowedHosts?: readonly string[];
  retryDelaysMs?: readonly number[];
  onProgress?: (progress: ModelDownloadProgress) => void;
}

export class ModelDownloadError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly retryable = false,
  ) {
    super(message);
    this.name = "ModelDownloadError";
  }
}

export function installedModelPath(
  userDataDirectory: string,
  filename: string = QWEN_MODEL.filename,
): string {
  return path.join(userDataDirectory, "models", filename);
}

function abortError(): ModelDownloadError {
  return new ModelDownloadError("模型下载已取消", "MODEL_DOWNLOAD_CANCELLED");
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw abortError();
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  if (ms <= 0) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(abortError());
      },
      { once: true },
    );
  });
}

export function validateModelDownloadUrl(
  value: string | URL,
  allowedHosts: readonly string[] = DEFAULT_ALLOWED_HOSTS,
): URL {
  let url: URL;
  try {
    url = value instanceof URL ? new URL(value) : new URL(value);
  } catch {
    throw new ModelDownloadError("模型下载地址无效", "MODEL_URL_INVALID");
  }
  if (url.protocol !== "https:") {
    throw new ModelDownloadError("模型下载必须使用 HTTPS", "MODEL_URL_INSECURE");
  }
  if (/^https?:\/\/[^/]*@/.test(url.href) || url.port) {
    throw new ModelDownloadError(
      "模型下载地址包含不允许的凭据或端口",
      "MODEL_URL_INVALID",
    );
  }
  if (!allowedHosts.includes(url.hostname.toLowerCase())) {
    throw new ModelDownloadError(
      "模型下载跳转到了未授权的主机",
      "MODEL_HOST_NOT_ALLOWED",
    );
  }
  return url;
}

async function openWithRedirects(
  initialUrl: string,
  fetchImpl: ModelFetch,
  allowedHosts: readonly string[],
  signal?: AbortSignal,
  startOffset = 0,
): Promise<{ response: Response; url: URL; startOffset: number }> {
  let current = validateModelDownloadUrl(initialUrl, allowedHosts);
  for (let redirects = 0; redirects <= 5; redirects += 1) {
    throwIfAborted(signal);
    let response: Response;
    try {
      response = await fetchImpl(current, {
        method: "GET",
        redirect: "manual",
        signal,
        headers: {
          Accept: "application/octet-stream",
          ...(startOffset > 0 ? { Range: `bytes=${startOffset}-` } : {}),
        },
      });
    } catch (error) {
      if (signal?.aborted) throw abortError();
      if (error instanceof ModelDownloadError) throw error;
      throw new ModelDownloadError(
        "模型下载网络连接失败，请检查网络后重试",
        "MODEL_DOWNLOAD_NETWORK_ERROR",
        true,
      );
    }
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get("location");
      if (!location) {
        throw new ModelDownloadError(
          "模型下载跳转缺少目标地址",
          "MODEL_REDIRECT_INVALID",
        );
      }
      current = validateModelDownloadUrl(new URL(location, current), allowedHosts);
      continue;
    }
    if (!response.ok) {
      await response.body?.cancel().catch(() => undefined);
      if (response.status === 416 && startOffset > 0) {
        throw new ModelDownloadError(
          "模型服务器不接受断点续传范围",
          "MODEL_RESUME_RANGE_INVALID",
        );
      }
      throw new ModelDownloadError(
        `模型下载失败（HTTP ${response.status}）`,
        "MODEL_DOWNLOAD_HTTP_ERROR",
        response.status === 408 ||
          response.status === 429 ||
          response.status >= 500,
      );
    }
    if (startOffset > 0 && response.status === 206) {
      const match = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(
        response.headers.get("content-range") ?? "",
      );
      if (
        !match ||
        Number(match[1]) !== startOffset ||
        Number(match[2]) + 1 !== Number(match[3])
      ) {
        await response.body?.cancel().catch(() => undefined);
        throw new ModelDownloadError(
          "模型服务器返回了无效的续传范围",
          "MODEL_RESUME_RANGE_INVALID",
        );
      }
    }
    return {
      response,
      url: current,
      startOffset: response.status === 206 ? startOffset : 0,
    };
  }
  throw new ModelDownloadError("模型下载跳转次数过多", "MODEL_REDIRECT_LIMIT");
}

async function unlinkQuietly(file: string): Promise<void> {
  await fs.rm(file, { force: true }).catch(() => undefined);
}

async function syncDirectory(directory: string): Promise<void> {
  if (process.platform === "win32") return;
  const handle = await fs.open(directory, "r");
  try {
    await handle.sync();
  } finally {
    await handle.close();
  }
}

export async function sha256File(
  file: string,
  signal?: AbortSignal,
): Promise<string> {
  const hash = createHash("sha256");
  const handle = await fs.open(file, "r");
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  try {
    for (;;) {
      throwIfAborted(signal);
      const { bytesRead } = await handle.read(buffer, 0, buffer.length, null);
      if (!bytesRead) break;
      hash.update(buffer.subarray(0, bytesRead));
    }
  } finally {
    await handle.close();
  }
  return hash.digest("hex");
}

export async function verifyModelFile(
  file: string,
  expected: { bytes: number; sha256: string } = QWEN_MODEL,
  signal?: AbortSignal,
): Promise<boolean> {
  try {
    const stat = await fs.stat(file);
    if (!stat.isFile() || stat.size !== expected.bytes) return false;
    return (await sha256File(file, signal)) === expected.sha256;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return false;
    throw error;
  }
}

async function downloadAttempt(
  options: VerifiedDownloadOptions,
  temporary: string,
): Promise<void> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const allowedHosts = options.allowedHosts ?? DEFAULT_ALLOWED_HOSTS;
  let resumeOffset = await fs
    .stat(temporary)
    .then((stat) => (stat.isFile() ? stat.size : 0))
    .catch(() => 0);
  if (resumeOffset > options.expectedBytes) {
    await unlinkQuietly(temporary);
    resumeOffset = 0;
  }
  const {
    response,
    startOffset,
  } = await openWithRedirects(
    options.url,
    fetchImpl,
    allowedHosts,
    options.signal,
    resumeOffset,
  );
  if (startOffset > 0) {
    const match = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(
      response.headers.get("content-range") ?? "",
    );
    if (!match || Number(match[3]) !== options.expectedBytes) {
      await response.body?.cancel().catch(() => undefined);
      throw new ModelDownloadError(
        "模型服务器返回了错误的文件总大小",
        "MODEL_SIZE_MISMATCH",
      );
    }
  }
  if (resumeOffset > 0 && startOffset === 0) resumeOffset = 0;
  const contentLength = response.headers.get("content-length");
  if (contentLength !== null) {
    const announced = Number(contentLength);
    if (
      !Number.isSafeInteger(announced) ||
      announced !== options.expectedBytes - resumeOffset
    ) {
      throw new ModelDownloadError(
        "模型文件大小与固定清单不一致",
        "MODEL_SIZE_MISMATCH",
      );
    }
  }
  if (!response.body) {
    throw new ModelDownloadError(
      "模型下载响应没有文件内容",
      "MODEL_DOWNLOAD_EMPTY",
      true,
    );
  }

  const hash = createHash("sha256");
  if (resumeOffset > 0) {
    const handle = await fs.open(temporary, "r");
    const buffer = Buffer.allocUnsafe(1024 * 1024);
    let position = 0;
    try {
      while (position < resumeOffset) {
        throwIfAborted(options.signal);
        const length = Math.min(buffer.length, resumeOffset - position);
        const { bytesRead } = await handle.read(buffer, 0, length, position);
        if (!bytesRead) {
          throw new ModelDownloadError(
            "模型续传文件不完整",
            "MODEL_SIZE_MISMATCH",
          );
        }
        hash.update(buffer.subarray(0, bytesRead));
        position += bytesRead;
      }
    } finally {
      await handle.close();
    }
  }

  options.onProgress?.({
    phase: "starting",
    received: resumeOffset,
    total: options.expectedBytes,
  });
  const handle = await fs.open(temporary, resumeOffset > 0 ? "r+" : "w", 0o600);
  let received = resumeOffset;
  try {
    await handle.truncate(resumeOffset);
    const reader = response.body.getReader();
    for (;;) {
      throwIfAborted(options.signal);
      let chunk: ReadableStreamReadResult<Uint8Array>;
      try {
        chunk = await reader.read();
      } catch (error) {
        if (options.signal?.aborted) throw abortError();
        throw new ModelDownloadError(
          "模型下载连接中断，可稍后从断点继续",
          "MODEL_DOWNLOAD_NETWORK_ERROR",
          true,
        );
      }
      const { done, value } = chunk;
      if (done) break;
      if (!value?.byteLength) continue;
      const chunkStart = received;
      if (chunkStart + value.byteLength > options.expectedBytes) {
        await reader.cancel().catch(() => undefined);
        throw new ModelDownloadError(
          "模型文件超过固定大小",
          "MODEL_SIZE_MISMATCH",
        );
      }
      hash.update(value);
      let written = 0;
      while (written < value.byteLength) {
        const result = await handle.write(
          value,
          written,
          value.byteLength - written,
          chunkStart + written,
        );
        if (!result.bytesWritten) {
          throw new ModelDownloadError(
            "模型文件写入中断",
            "MODEL_DOWNLOAD_WRITE_FAILED",
            true,
          );
        }
        written += result.bytesWritten;
      }
      received += value.byteLength;
      options.onProgress?.({
        phase: "downloading",
        received,
        total: options.expectedBytes,
      });
    }
    await handle.sync();
  } finally {
    await handle.close();
  }

  if (received !== options.expectedBytes) {
    throw new ModelDownloadError(
      "模型文件下载不完整",
      "MODEL_SIZE_MISMATCH",
      true,
    );
  }
  options.onProgress?.({
    phase: "verifying",
    received,
    total: options.expectedBytes,
  });
  const actualSha256 = hash.digest("hex");
  if (actualSha256 !== options.expectedSha256.toLowerCase()) {
    throw new ModelDownloadError(
      "模型文件校验失败，已丢弃下载内容",
      "MODEL_HASH_MISMATCH",
    );
  }
}

async function selectPartialFile(
  destination: string,
  expectedBytes: number,
): Promise<string> {
  const directory = path.dirname(destination);
  const prefix = `${path.basename(destination)}.`;
  const preferred = `${destination}.part`;
  let candidates: { file: string; mtimeMs: number }[] = [];
  try {
    candidates = await Promise.all(
      (await fs.readdir(directory))
        .filter((name) => name.startsWith(prefix) && name.endsWith(".part"))
        .map(async (name) => {
          const file = path.join(directory, name);
          const stat = await fs.lstat(file).catch(() => undefined);
          if (!stat?.isFile() || stat.size <= 0 || stat.size > expectedBytes) {
            return undefined;
          }
          return { file, mtimeMs: stat.mtimeMs };
        }),
    ).then((items) =>
      items.filter((item): item is { file: string; mtimeMs: number } => Boolean(item)),
    );
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  candidates.sort((left, right) => right.mtimeMs - left.mtimeMs);
  return candidates[0]?.file ?? preferred;
}

async function removePartialFiles(destination: string, keep?: string): Promise<void> {
  const directory = path.dirname(destination);
  const prefix = `${path.basename(destination)}.`;
  const entries = await fs.readdir(directory).catch(() => [] as string[]);
  await Promise.all(
    entries
      .filter((name) => name.startsWith(prefix) && name.endsWith(".part"))
      .map((name) => path.join(directory, name))
      .filter((file) => file !== keep)
      .map((file) => unlinkQuietly(file)),
  );
}

async function publishDownloadedFile(
  temporary: string,
  destination: string,
  expectedBytes: number,
  onProgress?: (progress: ModelDownloadProgress) => void,
): Promise<void> {
  try {
    await fs.rename(temporary, destination);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
    await fs.rm(destination, { force: true });
    await fs.rename(temporary, destination);
  }
  await syncDirectory(path.dirname(destination));
  await removePartialFiles(destination, temporary);
  onProgress?.({
    phase: "installed",
    received: expectedBytes,
    total: expectedBytes,
  });
}

export async function downloadVerifiedFile(
  options: VerifiedDownloadOptions,
): Promise<void> {
  if (
    !Number.isSafeInteger(options.expectedBytes) ||
    options.expectedBytes <= 0 ||
    !/^[a-f0-9]{64}$/i.test(options.expectedSha256)
  ) {
    throw new ModelDownloadError(
      "模型固定清单无效",
      "MODEL_MANIFEST_INVALID",
    );
  }
  await fs.mkdir(path.dirname(options.destination), {
    recursive: true,
    mode: 0o700,
  });
  const temporary = await selectPartialFile(
    options.destination,
    options.expectedBytes,
  );
  const retryDelays = options.retryDelaysMs ?? [750, 2_000];
  let lastError: unknown;
  let retriedFromScratch = false;
  for (let attempt = 0; attempt <= retryDelays.length; attempt += 1) {
    throwIfAborted(options.signal);
    try {
      const existing = await fs
        .stat(temporary)
        .then((stat) => (stat.isFile() ? stat.size : 0))
        .catch(() => 0);
      if (existing === options.expectedBytes) {
        if (
          await verifyModelFile(temporary, {
            bytes: options.expectedBytes,
            sha256: options.expectedSha256,
          })
        ) {
          await publishDownloadedFile(
            temporary,
            options.destination,
            options.expectedBytes,
            options.onProgress,
          );
          return;
        }
        await unlinkQuietly(temporary);
      }
      await downloadAttempt(options, temporary);
      await publishDownloadedFile(
        temporary,
        options.destination,
        options.expectedBytes,
        options.onProgress,
      );
      return;
    } catch (error) {
      lastError = error;
      if (options.signal?.aborted) {
        await unlinkQuietly(temporary);
        throw abortError();
      }
      const resumeOffset = await fs
        .stat(temporary)
        .then((stat) => (stat.isFile() ? stat.size : 0))
        .catch(() => 0);
      if (
        error instanceof ModelDownloadError &&
        error.code === "MODEL_HASH_MISMATCH" &&
        resumeOffset > 0 &&
        !retriedFromScratch
      ) {
        retriedFromScratch = true;
        await unlinkQuietly(temporary);
        continue;
      }
      const retryable =
        error instanceof ModelDownloadError
          ? error.retryable
          : error instanceof TypeError;
      if (!retryable) {
        if (
          error instanceof ModelDownloadError &&
          ![
            "MODEL_REDIRECT_INVALID",
            "MODEL_REDIRECT_LIMIT",
          ].includes(error.code)
        ) {
          await unlinkQuietly(temporary);
        }
        throw error;
      }
      if (attempt === retryDelays.length) throw error;
      await wait(retryDelays[attempt], options.signal);
    }
  }
  throw lastError;
}
