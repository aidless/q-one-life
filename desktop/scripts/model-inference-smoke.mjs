import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { getLlama, LlamaChatSession } from "node-llama-cpp";

const expectedBytes = 639_446_688;
const expectedSha256 = "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031";
const defaultModelPath =
  process.env.QONE_MODEL_SMOKE_PATH ??
  "/home/liuzewen/.cache/qone-model-qwen3-0.6b-20261027/models/Qwen3-0.6B-Q8_0.gguf";

function argument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function fail(error) {
  const code =
    error && typeof error === "object" && typeof error.code === "string"
      ? error.code
      : "MODEL_INFERENCE_SMOKE_FAILED";
  console.error(
    `QONE_MODEL_INFERENCE_SMOKE_FAILED ${JSON.stringify({
      code,
      message: error instanceof Error ? error.message : String(error),
    })}`,
  );
  process.exitCode = 1;
}

async function sha256File(file) {
  const hash = createHash("sha256");
  const handle = await fs.open(file, "r");
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  try {
    for (;;) {
      const { bytesRead } = await handle.read(buffer, 0, buffer.length, null);
      if (!bytesRead) break;
      hash.update(buffer.subarray(0, bytesRead));
    }
  } finally {
    await handle.close();
  }
  return hash.digest("hex");
}

async function main() {
  const modelPath = path.resolve(argument("--model") ?? defaultModelPath);
  const gpu = argument("--gpu") === "auto" ? "auto" : false;
  const stat = await fs.stat(modelPath).catch(() => undefined);
  if (!stat?.isFile()) {
    throw Object.assign(new Error(`model not found: ${modelPath}`), {
      code: "LOCAL_MODEL_FILE_MISSING",
    });
  }
  if (stat.size !== expectedBytes) {
    throw Object.assign(new Error(`model size mismatch: ${stat.size}`), {
      code: "MODEL_SIZE_MISMATCH",
    });
  }
  const digest = await sha256File(modelPath);
  if (digest !== expectedSha256) {
    throw Object.assign(new Error("model hash mismatch"), {
      code: "MODEL_HASH_MISMATCH",
    });
  }

  const llama = await getLlama({
    gpu,
    build: "never",
    usePrebuiltBinaries: true,
    progressLogs: false,
    logLevel: "error",
  });
  const model = await llama.loadModel({
    modelPath,
    gpuLayers: gpu === "auto" ? "auto" : 0,
    useMmap: "auto",
  });
  const context = await model.createContext({
    contextSize: 4_096,
    sequences: 1,
    flashAttention: "auto",
  });
  const sequence = context.getSequence();
  const session = new LlamaChatSession({
    contextSequence: sequence,
    systemPrompt: "Return only JSON with the requested field. Do not explain.",
    autoDisposeSequence: true,
    forceAddSystemPrompt: true,
  });
  try {
    const grammar = await llama.createGrammarForJsonSchema({
      type: "object",
      properties: { answer: { type: "string", enum: ["yes"] } },
      required: ["answer"],
      additionalProperties: false,
    });
    const text = await session.prompt('Return {"answer":"yes"}.', {
      maxTokens: 48,
      temperature: 0,
      grammar,
    });
    const parsed = JSON.parse(text);
    if (parsed?.answer !== "yes") {
      throw new Error(`unexpected structured output: ${text.slice(0, 200)}`);
    }
    console.log(
      `QONE_MODEL_INFERENCE_SMOKE_OK ${JSON.stringify({
        bytes: stat.size,
        sha256: digest,
        model: path.basename(modelPath),
        output: parsed,
        gpu: llama.gpu,
        buildType: llama.buildType,
        contextSize: 4_096,
      })}`,
    );
  } finally {
    session.dispose({ disposeSequence: true });
    context.dispose();
    model.dispose();
    llama.dispose();
  }
}

main().catch(fail);
