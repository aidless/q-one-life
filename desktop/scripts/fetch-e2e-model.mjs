import { promises as fs } from "node:fs";
import path from "node:path";
import {
  downloadVerifiedFile,
  QWEN_MODEL,
  verifyModelFile,
} from "../dist/model-files.js";

function argument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

async function main() {
  const outputValue = argument("--output");
  if (!outputValue) {
    throw new Error("--output is required");
  }
  const output = path.resolve(outputValue);
  if (await verifyModelFile(output, QWEN_MODEL)) {
    console.log(`QONE_E2E_MODEL_READY cached ${output}`);
    return;
  }

  await fs.rm(output, { force: true });
  let lastProgress = -1;
  await downloadVerifiedFile({
    url: QWEN_MODEL.url,
    expectedBytes: QWEN_MODEL.bytes,
    expectedSha256: QWEN_MODEL.sha256,
    destination: output,
    retryDelaysMs: [1_000, 3_000, 8_000],
    onProgress: ({ phase, received, total }) => {
      if (phase !== "downloading" || !total) return;
      const progress = Math.floor((received / total) * 10) * 10;
      if (progress > lastProgress) {
        lastProgress = progress;
        console.log(`QONE_E2E_MODEL_PROGRESS ${progress}%`);
      }
    },
  });
  if (!(await verifyModelFile(output, QWEN_MODEL))) {
    throw new Error("downloaded E2E model failed final verification");
  }
  console.log(`QONE_E2E_MODEL_READY downloaded ${output}`);
}

main().catch((error) => {
  console.error(
    `QONE_E2E_MODEL_FAILED ${error instanceof Error ? error.message : String(error)}`,
  );
  process.exitCode = 1;
});
