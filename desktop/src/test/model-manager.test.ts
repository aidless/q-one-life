import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  ManagedModel,
  ModelManager,
  publicModelStatus,
} from "../model-manager";
import { ModelDownloadError } from "../model-files";

const payload = Buffer.from("Q-One model manager fixture\n".repeat(64));
const sha256 = createHash("sha256").update(payload).digest("hex");
const model: ManagedModel = {
  name: "fixture.gguf",
  repository: "Q-One/test",
  revision: "a".repeat(40),
  bytes: payload.length,
  sha256,
  license: "Apache-2.0",
  url: "https://huggingface.co/Q-One/test/resolve/main/fixture.gguf",
};

function responseFor(bytes: Buffer): Response {
  return new Response(new Uint8Array(bytes), {
    status: 200,
    headers: { "content-length": String(bytes.length) },
  });
}

test("model manager verifies, installs, and removes a pinned file", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-manager-"));
  const manager = new ModelManager(folder, {
    model,
    retryDelaysMs: [],
    fetchImpl: async () => responseFor(payload),
  });
  await manager.initialize();
  assert.equal(manager.status().phase, "not_installed");
  await manager.startDownload();
  assert.equal(manager.status().phase, "installed");
  assert.equal(manager.status().verified, true);
  assert.deepEqual(await fs.readFile(manager.filePath), payload);
  await manager.remove();
  assert.equal(manager.status().phase, "not_installed");
  await assert.rejects(fs.stat(manager.filePath), { code: "ENOENT" });
});

test("corrupt installed files are reported and can be replaced", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-manager-"));
  const manager = new ModelManager(folder, {
    model,
    retryDelaysMs: [],
    fetchImpl: async () => responseFor(payload),
  });
  await fs.mkdir(path.dirname(manager.filePath), { recursive: true });
  await fs.writeFile(manager.filePath, Buffer.concat([payload, Buffer.from("corrupt")]));
  await manager.initialize();
  assert.equal(manager.status().phase, "error");
  assert.equal(manager.status().installed, false);
  assert.equal(manager.status().error_code, "MODEL_FILE_CORRUPT");
  await manager.startDownload();
  assert.equal(manager.status().phase, "installed");
  assert.deepEqual(await fs.readFile(manager.filePath), payload);
});

test("a cancelled download leaves no published or partial model", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-manager-"));
  const manager = new ModelManager(folder, {
    model,
    retryDelaysMs: [],
    fetchImpl: (_input, init) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener(
          "abort",
          () => reject(new DOMException("aborted", "AbortError")),
          { once: true },
        );
      }),
  });
  const task = manager.startDownload();
  await new Promise((resolve) => setTimeout(resolve, 20));
  manager.cancel();
  await assert.rejects(task, (error: unknown) =>
    Boolean(error && typeof error === "object" && "code" in error &&
      (error as { code?: string }).code === "MODEL_DOWNLOAD_CANCELLED"),
  );
  assert.equal(manager.status().phase, "not_installed");
  assert.equal(manager.status().error_code, "MODEL_DOWNLOAD_CANCELLED");
  await assert.rejects(fs.stat(manager.filePath), { code: "ENOENT" });
  assert.deepEqual(
    (await fs.readdir(path.dirname(manager.filePath))).filter((name) =>
      name.endsWith(".part"),
    ),
    [],
  );
});

test("renderer-facing model status never exposes paths, URLs, or tokens", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-manager-"));
  const manager = new ModelManager(folder, { model });
  const status = publicModelStatus(manager.status(), false, "LOCAL_MODEL_SERVICE_FAILED");
  const serialized = JSON.stringify(status);
  assert.doesNotMatch(serialized, /token|api[_-]?key|local_url|filePath|fixture\.gguf\?/i);
  assert.equal(status.model && (status.model as Record<string, unknown>).name, "fixture.gguf");
  assert.equal(status.service_error, "LOCAL_MODEL_SERVICE_FAILED");
});

test("model manager falls back to an identically pinned second source", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-manager-"));
  const fallbackUrl = "https://modelscope.cn/Q-One/test/resolve/fixture.gguf";
  const requested: string[] = [];
  const manager = new ModelManager(folder, {
    model: { ...model, fallbackUrls: [fallbackUrl] },
    retryDelaysMs: [],
    fetchImpl: async (input) => {
      const url = String(input);
      requested.push(url);
      if (url === model.url) {
        throw new ModelDownloadError(
          "primary unavailable",
          "MODEL_DOWNLOAD_NETWORK_ERROR",
          true,
        );
      }
      return responseFor(payload);
    },
  });
  await manager.initialize();
  await manager.startDownload();
  assert.deepEqual(requested, [model.url, fallbackUrl]);
  assert.equal(manager.status().phase, "installed");
  assert.equal(manager.status().verified, true);
  assert.deepEqual(await fs.readFile(manager.filePath), payload);
});
