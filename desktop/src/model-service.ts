import { randomBytes } from "node:crypto";
import { promises as fs } from "node:fs";
import type { AddressInfo } from "node:net";
import { createLocalModelServer, LocalGenerationRequest, LocalGenerationResult } from "./local-model-protocol";

type LlamaModule = typeof import(
  "node-llama-cpp",
  { with: { "resolution-mode": "import" } }
);
type LlamaBinding = Awaited<ReturnType<LlamaModule["getLlama"]>>;
type LlamaModel = Awaited<ReturnType<LlamaBinding["loadModel"]>>;
type LlamaContext = Awaited<ReturnType<LlamaModel["createContext"]>>;
type ChatSession = InstanceType<LlamaModule["LlamaChatSession"]>;

interface ParentPort {
  on(event: "message", listener: (message: unknown) => void): void;
  postMessage(message: unknown): void;
}

const MODEL_NAME = "Qwen3-0.6B-Q8_0";
const CONTEXT_SIZE = 8_192;
const parentPort = (process as NodeJS.Process & { parentPort?: ParentPort }).parentPort;

if (!parentPort) {
  console.error("Q-One local model service requires an Electron utility-process parent");
  process.exit(2);
}

const importEsm = new Function("specifier", "return import(specifier)") as (
  specifier: string,
) => Promise<LlamaModule>;

let modulePromise: Promise<{
  module: LlamaModule;
  llama: LlamaBinding;
  context: LlamaContext;
}> | undefined;
let running = false;
let queued = 0;
let generationTail: Promise<void> = Promise.resolve();

function codedError(code: string, message: string): Error & { code: string } {
  return Object.assign(new Error(message), { code });
}

function classifyError(error: unknown): Error & { code: string } {
  const original = error instanceof Error ? error : new Error(String(error));
  const text = original.message.toLowerCase();
  if (
    original.name === "InsufficientMemoryError" ||
    /out of memory|cannot allocate|failed to allocate|insufficient memory/.test(text)
  ) {
    return codedError(
      "LOCAL_MODEL_INSUFFICIENT_MEMORY",
      "设备内存不足，已停止本地推理并保留规则推荐",
    );
  }
  if (original.name === "AbortError" || /aborted|abort signal/.test(text)) {
    return codedError("LOCAL_MODEL_CANCELLED", "本地模型请求已取消");
  }
  if (/no binary|binding|native|dlopen|shared library/.test(text)) {
    return codedError(
      "LOCAL_MODEL_BACKEND_UNAVAILABLE",
      "本地推理组件无法在此设备加载",
    );
  }
  return codedError("LOCAL_MODEL_FAILED", original.message || "本地模型推理失败");
}

async function loadModel(): Promise<{
  module: LlamaModule;
  llama: LlamaBinding;
  context: LlamaContext;
}> {
  if (modulePromise) return modulePromise;
  modulePromise = (async () => {
    const modelPath = process.env.QONE_MODEL_PATH;
    if (!modelPath) throw codedError("LOCAL_MODEL_FILE_MISSING", "缺少本地模型路径");
    const stat = await fs.stat(modelPath).catch(() => undefined);
    if (!stat?.isFile() || stat.size <= 0) {
      throw codedError("LOCAL_MODEL_FILE_MISSING", "本地模型文件不存在");
    }
    const module = await importEsm("node-llama-cpp");
    const llama = await module.getLlama({
      gpu: "auto",
      build: "never",
      usePrebuiltBinaries: true,
    });
    const model = await llama.loadModel({
      modelPath,
      gpuLayers: "auto",
      useMmap: "auto",
    });
    const context = await model.createContext({
      contextSize: CONTEXT_SIZE,
      sequences: 1,
      flashAttention: "auto",
    });
    return { module, llama, context };
  })().catch((error) => {
    modulePromise = undefined;
    throw classifyError(error);
  });
  return modulePromise;
}

function buildPrompt(request: LocalGenerationRequest): {
  systemPrompt?: string;
  prompt: string;
} {
  const system = request.messages
    .filter((message) => message.role === "system")
    .map((message) => message.content.trim())
    .filter(Boolean)
    .join("\n\n");
  const prompt = request.messages
    .filter((message) => message.role !== "system")
    .map((message) => `${message.role.toUpperCase()}:\n${message.content}`)
    .join("\n\n")
    .trim();
  if (!prompt) throw codedError("INVALID_REQUEST", "本地模型请求缺少用户内容");
  return {
    ...(system ? { systemPrompt: system } : {}),
    prompt,
  };
}

async function generate(request: LocalGenerationRequest): Promise<LocalGenerationResult> {
  const loaded = await loadModel();
  const sequence = loaded.context.getSequence();
  const prepared = buildPrompt(request);
  const session: ChatSession = new loaded.module.LlamaChatSession({
    contextSequence: sequence,
    ...(prepared.systemPrompt ? { systemPrompt: prepared.systemPrompt } : {}),
    autoDisposeSequence: true,
    forceAddSystemPrompt: true,
  });
  try {
    const before = sequence.tokenMeter.getState();
    const grammar = request.responseSchema
      ? await loaded.llama.createGrammarForJsonSchema(request.responseSchema as never)
      : undefined;
    const text = await session.prompt(prepared.prompt, {
      maxTokens: request.maxTokens,
      temperature: request.temperature,
      signal: request.signal,
      stopOnAbortSignal: false,
      ...(grammar ? { grammar } : {}),
    });
    const after = sequence.tokenMeter.getState();
    return {
      text,
      promptTokens: Math.max(0, after.usedInputTokens - before.usedInputTokens),
      completionTokens: Math.max(0, after.usedOutputTokens - before.usedOutputTokens),
    };
  } finally {
    session.dispose({ disposeSequence: true });
  }
}

function serialized(request: LocalGenerationRequest): Promise<LocalGenerationResult> {
  queued += 1;
  const run = generationTail.then(async () => {
    running = true;
    try {
      return await generate(request);
    } catch (error) {
      throw classifyError(error);
    } finally {
      running = false;
      queued -= 1;
    }
  });
  generationTail = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

async function main(): Promise<void> {
  const token = randomBytes(32).toString("base64url");
  const server = createLocalModelServer({
    token,
    modelName: MODEL_NAME,
    generator: serialized,
    modelState: () => ({
      loaded: Boolean(modulePromise),
      busy: running,
      queued,
    }),
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve());
  });
  const address = server.address() as AddressInfo;
  parentPort.postMessage({
    type: "ready",
    port: address.port,
    pid: process.pid,
    token,
    model: MODEL_NAME,
  });

  let closing = false;
  const shutdown = () => {
    if (closing) return;
    closing = true;
    server.close(() => process.exit(0));
    const timer = setTimeout(() => process.exit(0), 1_500);
    timer.unref();
  };
  parentPort.on("message", (message: unknown) => {
    if (
      message &&
      typeof message === "object" &&
      (message as Record<string, unknown>).type === "shutdown"
    ) {
      shutdown();
    }
  });
  process.once("SIGTERM", shutdown);
  process.once("SIGINT", shutdown);
}

void main().catch((error) => {
  const classified = classifyError(error);
  parentPort?.postMessage({
    type: "error",
    code: classified.code,
    message: classified.message,
  });
  setTimeout(() => process.exit(1), 10);
});
