import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  DEFAULT_ALLOWED_HOSTS,
  downloadVerifiedFile,
  ModelDownloadError,
  validateModelDownloadUrl,
  verifyModelFile,
} from "../model-files";

const payload = Buffer.from("Q-One pinned model fixture\n".repeat(128));
const payloadSha = createHash("sha256").update(payload).digest("hex");
const allowedHosts = ["models.example", "cdn.example"];

test("verified download follows approved redirects and publishes atomically", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-model-"));
  const destination = path.join(folder, "models", "fixture.gguf");
  const phases: string[] = [];
  const requests: string[] = [];
  const fakeFetch = async (input: string | URL): Promise<Response> => {
    const url = String(input);
    requests.push(url);
    if (url.startsWith("https://models.example/")) {
      return new Response(null, {
        status: 302,
        headers: { location: "https://cdn.example/file" },
      });
    }
    return new Response(payload, {
      status: 200,
      headers: { "content-length": String(payload.length) },
    });
  };

  await downloadVerifiedFile({
    url: "https://models.example/start",
    expectedBytes: payload.length,
    expectedSha256: payloadSha,
    destination,
    fetchImpl: fakeFetch,
    allowedHosts,
    retryDelaysMs: [],
    onProgress: (progress) => phases.push(progress.phase),
  });

  assert.deepEqual(requests, [
    "https://models.example/start",
    "https://cdn.example/file",
  ]);
  assert.deepEqual(await fs.readFile(destination), payload);
  assert.equal(await verifyModelFile(destination, {
    bytes: payload.length,
    sha256: payloadSha,
  }), true);
  assert.deepEqual(phases, ["starting", "downloading", "verifying", "installed"]);
  assert.deepEqual(
    (await fs.readdir(path.dirname(destination))).filter((name) =>
      name.endsWith(".part"),
    ),
    [],
  );
});

test("verified download resumes a partial file with a validated range request", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-model-"));
  const destination = path.join(folder, "models", "fixture.gguf");
  const split = 700;
  let requestedRange = "";
  await fs.mkdir(path.dirname(destination), { recursive: true });
  await fs.writeFile(`${destination}.part`, payload.subarray(0, split));

  await downloadVerifiedFile({
    url: "https://models.example/file",
    expectedBytes: payload.length,
    expectedSha256: payloadSha,
    destination,
    fetchImpl: async (_input, init) => {
      requestedRange = new Headers(init?.headers).get("range") ?? "";
      return new Response(payload.subarray(split), {
        status: 206,
        headers: {
          "content-length": String(payload.length - split),
          "content-range": `bytes ${split}-${payload.length - 1}/${payload.length}`,
        },
      });
    },
    allowedHosts,
    retryDelaysMs: [],
  });

  assert.equal(requestedRange, `bytes=${split}-`);
  assert.deepEqual(await fs.readFile(destination), payload);
  assert.deepEqual(
    (await fs.readdir(path.dirname(destination))).filter((name) =>
      name.endsWith(".part"),
    ),
    [],
  );
});

test("hash mismatch never publishes the downloaded bytes", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-model-"));
  const destination = path.join(folder, "fixture.gguf");
  await assert.rejects(
    downloadVerifiedFile({
      url: "https://models.example/file",
      expectedBytes: payload.length,
      expectedSha256: "0".repeat(64),
      destination,
      fetchImpl: async () =>
        new Response(payload, {
          status: 200,
          headers: { "content-length": String(payload.length) },
        }),
      allowedHosts,
      retryDelaysMs: [],
    }),
    (error: unknown) =>
      error instanceof ModelDownloadError && error.code === "MODEL_HASH_MISMATCH",
  );
  await assert.rejects(fs.stat(destination), { code: "ENOENT" });
  assert.deepEqual(
    (await fs.readdir(folder)).filter((name) => name.endsWith(".part")),
    [],
  );
});

test("size mismatch and unapproved redirects fail before writing", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-model-"));
  const destination = path.join(folder, "fixture.gguf");
  await assert.rejects(
    downloadVerifiedFile({
      url: "https://models.example/file",
      expectedBytes: payload.length,
      expectedSha256: payloadSha,
      destination,
      fetchImpl: async () =>
        new Response(payload, {
          status: 200,
          headers: { "content-length": "1" },
        }),
      allowedHosts,
      retryDelaysMs: [],
    }),
    (error: unknown) =>
      error instanceof ModelDownloadError &&
      error.code === "MODEL_SIZE_MISMATCH",
  );
  await assert.rejects(
    downloadVerifiedFile({
      url: "https://models.example/file",
      expectedBytes: payload.length,
      expectedSha256: payloadSha,
      destination,
      fetchImpl: async () =>
        new Response(null, {
          status: 302,
          headers: { location: "https://untrusted.example/file" },
        }),
      allowedHosts,
      retryDelaysMs: [],
    }),
    (error: unknown) =>
      error instanceof ModelDownloadError &&
      error.code === "MODEL_HOST_NOT_ALLOWED",
  );
  await assert.rejects(fs.stat(destination), { code: "ENOENT" });
});

test("pre-aborted downloads exit as cancelled", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-model-"));
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    downloadVerifiedFile({
      url: "https://models.example/file",
      expectedBytes: payload.length,
      expectedSha256: payloadSha,
      destination: path.join(folder, "fixture.gguf"),
      signal: controller.signal,
      allowedHosts,
    }),
    (error: unknown) =>
      error instanceof ModelDownloadError &&
      error.code === "MODEL_DOWNLOAD_CANCELLED",
  );
});

test("network failures become a retryable stable error code", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-model-"));
  await assert.rejects(
    downloadVerifiedFile({
      url: "https://models.example/file",
      expectedBytes: payload.length,
      expectedSha256: payloadSha,
      destination: path.join(folder, "fixture.gguf"),
      fetchImpl: async () => {
        throw new TypeError("fetch failed");
      },
      allowedHosts,
      retryDelaysMs: [],
    }),
    (error: unknown) =>
      error instanceof ModelDownloadError &&
      error.code === "MODEL_DOWNLOAD_NETWORK_ERROR" &&
      error.retryable,
  );
});

test("a rejected resume range is reported without publishing bytes", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-model-"));
  const destination = path.join(folder, "fixture.gguf");
  await fs.mkdir(path.dirname(destination), { recursive: true });
  await fs.writeFile(`${destination}.part`, payload.subarray(0, 100));
  await assert.rejects(
    downloadVerifiedFile({
      url: "https://models.example/file",
      expectedBytes: payload.length,
      expectedSha256: payloadSha,
      destination,
      fetchImpl: async () =>
        new Response(null, {
          status: 416,
          headers: { "content-range": `bytes */${payload.length}` },
        }),
      allowedHosts,
      retryDelaysMs: [],
    }),
    (error: unknown) =>
      error instanceof ModelDownloadError &&
      error.code === "MODEL_RESUME_RANGE_INVALID",
  );
  await assert.rejects(fs.stat(destination), { code: "ENOENT" });
});

test("model CDN allowlist uses exact hosts rather than suffix matching", () => {
  assert.equal(
    validateModelDownloadUrl(
      "https://us.aws.cdn.hf.co/xet-bridge-us/model.gguf",
    ).hostname,
    "us.aws.cdn.hf.co",
  );
  const approved = "us.aws.cdn.hf.co";
  assert.ok(DEFAULT_ALLOWED_HOSTS.includes(approved));
  for (const rejected of [
    "evil.us.aws.cdn.hf.co",
    "us.aws.cdn.hf.co.evil.example",
    "notus.aws.cdn.hf.co",
    "evil.modelscope.cn",
    "modelscope.cn.evil.example",
    "cdn-lfs-cn-1.modelscope.cn.evil.example",
  ]) {
    assert.throws(
      () => validateModelDownloadUrl(`https://${rejected}/model.gguf`),
      (error: unknown) =>
        error instanceof ModelDownloadError &&
        error.code === "MODEL_HOST_NOT_ALLOWED",
    );
  }
});
