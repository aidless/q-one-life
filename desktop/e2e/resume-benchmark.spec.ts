import { _electron as electron, ElectronApplication, Page, expect, test } from "@playwright/test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createReadStream, promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

const appDirectory = path.resolve(__dirname, "..");
const benchmarkEnabled = process.env.QONE_RUN_RESUME_BENCHMARK === "1";
const sidecarValue = process.env.QONE_SIDECAR_BIN;
const localModelValue = process.env.QONE_E2E_LOCAL_MODEL_PATH;
const benchmarkRoot = path.resolve(
  process.env.QONE_RESUME_BENCHMARK_OUTPUT ??
    path.join(appDirectory, "..", "artifacts", "resume-kit", "benchmark"),
);
const tasksPath = path.join(appDirectory, "benchmarks", "resume-tasks.json");

interface BenchmarkTask {
  id: string;
  title: string;
  success_criterion: string;
  domain: string;
  priority: number;
}

interface PlannerItem {
  candidate_id: string;
  source: string;
  input_sha256: string;
  proposal_sha256: string;
  first_step?: string;
  done_when?: string;
  title?: string;
  minutes?: number;
}

interface PlannerState {
  provider: string;
  status: string;
  error?: string | null;
  input_sha256?: string;
  items: PlannerItem[];
}

interface CaseResult {
  id: string;
  completed: boolean;
  valid_goal_match: boolean;
  trace_bound: boolean;
  actionable: boolean;
  latency_ms: number;
  configured_provider: string;
  planner_status: string;
  effective_source?: string;
  item_title?: string;
  error?: string;
}

interface BenchmarkSummary {
  schema: "q-one-resume-benchmark-result-v1";
  generated_at: string;
  mode: "rules" | "hybrid-local";
  qualification: string;
  task_count: number;
  completed: number;
  valid_goal_matches: number;
  trace_bound: number;
  actionable: number;
  average_latency_ms: number;
  maximum_latency_ms: number;
  electron_working_set_kb: number;
  electron_cpu_percent: number;
  provider_counts: Record<string, number>;
  cases: CaseResult[];
  runtime: Record<string, unknown>;
}

async function sha256File(file: string): Promise<string> {
  const digest = createHash("sha256");
  for await (const chunk of createReadStream(file)) digest.update(chunk);
  return digest.digest("hex");
}

async function resolveSidecar(): Promise<string> {
  if (!sidecarValue) throw new Error("QONE_SIDECAR_BIN is required");
  return path.isAbsolute(sidecarValue)
    ? sidecarValue
    : path.resolve(appDirectory, sidecarValue);
}

async function prepareLocalModelProfile(profile: string, source: string): Promise<void> {
  const modelDirectory = path.join(profile, "models");
  const destination = path.join(modelDirectory, "Qwen3-0.6B-Q8_0.gguf");
  await fs.mkdir(modelDirectory, { recursive: true });
  try {
    await fs.link(source, destination);
  } catch {
    try {
      await fs.symlink(source, destination);
    } catch {
      await fs.copyFile(source, destination);
    }
  }
}

async function launchDesktop(
  profile: string,
  useLocalModel: boolean,
): Promise<{ app: ElectronApplication; page: Page }> {
  if (useLocalModel) {
    if (!localModelValue) throw new Error("QONE_E2E_LOCAL_MODEL_PATH is required");
    await prepareLocalModelProfile(profile, localModelValue);
  }
  const app = await electron.launch({
    args: [
      appDirectory,
      `--user-data-dir=${profile}`,
      "--disable-gpu",
      "--disable-features=CalculateNativeWinOcclusion",
    ],
    env: {
      ...process.env,
      QONE_SIDECAR_BIN: await resolveSidecar(),
      QONE_SKIP_MIGRATION_PROMPT: "1",
    },
  });
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");
  return { app, page };
}

async function api(
  page: Page,
  route: string,
  method: "GET" | "POST" | "PATCH",
  body?: Record<string, unknown>,
): Promise<{ status: number; payload: any }> {
  return page.evaluate(
    async ({ route, method, body }) => {
      const response = await fetch(route, {
        method,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-QOne-Client": "web",
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      return {
        status: response.status,
        payload: await response.json(),
      };
    },
    { route, method, body },
  );
}

async function processMetrics(
  app: ElectronApplication,
): Promise<{ workingSetKb: number; cpuPercent: number }> {
  return app.evaluate(({ app }) => {
    const metrics = app.getAppMetrics();
    return {
      workingSetKb: metrics.reduce(
        (total, metric) => total + (metric.memory?.workingSetSize ?? 0),
        0,
      ),
      cpuPercent: metrics.reduce(
        (total, metric) => total + (metric.cpu?.percentCPUUsage ?? 0),
        0,
      ),
    };
  });
}

async function waitForPlanner(
  page: Page,
  goalId: string,
  mode: "rules" | "hybrid-local",
): Promise<{ planner: PlannerState; latencyMs: number }> {
  const started = Date.now();
  const timeoutMs = mode === "hybrid-local" ? 300_000 : 30_000;
  let last: PlannerState = {
    provider: "unknown",
    status: "unknown",
    items: [],
  };
  while (Date.now() - started < timeoutMs) {
    const response = await api(page, "/api/planner", "GET");
    assert.equal(response.status, 200);
    last = response.payload as PlannerState;
    const item = last.items.find(
      (candidate) => candidate.candidate_id === `goal:${goalId}`,
    );
    if (item && mode === "rules") break;
    if (
      item &&
      mode === "hybrid-local" &&
      last.provider === "local" &&
      last.status === "ready"
    ) {
      break;
    }
    if (
      item &&
      mode === "hybrid-local" &&
      new Set(["rules", "error"]).has(last.status)
    ) {
      break;
    }
    await page.waitForTimeout(500);
  }
  return { planner: last, latencyMs: Date.now() - started };
}

function summarize(
  mode: "rules" | "hybrid-local",
  cases: CaseResult[],
  metrics: { workingSetKb: number; cpuPercent: number },
  runtime: Record<string, unknown>,
): BenchmarkSummary {
  return {
    schema: "q-one-resume-benchmark-result-v1",
    generated_at: new Date().toISOString(),
    mode,
    qualification:
      "Small local engineering acceptance set; not an external validity study or evidence of real-world benefit.",
    task_count: cases.length,
    completed: cases.filter((item) => item.completed).length,
    valid_goal_matches: cases.filter((item) => item.valid_goal_match).length,
    trace_bound: cases.filter((item) => item.trace_bound).length,
    actionable: cases.filter((item) => item.actionable).length,
    average_latency_ms: Math.round(
      cases.reduce((total, item) => total + item.latency_ms, 0) /
        Math.max(cases.length, 1),
    ),
    maximum_latency_ms: Math.max(0, ...cases.map((item) => item.latency_ms)),
    electron_working_set_kb: Math.round(metrics.workingSetKb),
    electron_cpu_percent: Number(metrics.cpuPercent.toFixed(2)),
    provider_counts: cases.reduce<Record<string, number>>((counts, item) => {
      const provider = item.effective_source?.split(":", 1)[0] ?? "none";
      counts[provider] = (counts[provider] ?? 0) + 1;
      return counts;
    }, {}),
    cases,
    runtime,
  };
}

async function runBenchmark(mode: "rules" | "hybrid-local"): Promise<void> {
  test.skip(!benchmarkEnabled, "set QONE_RUN_RESUME_BENCHMARK=1 to run");
  test.skip(!sidecarValue, "QONE_SIDECAR_BIN is required");
  if (mode === "hybrid-local") {
    test.skip(!localModelValue, "QONE_E2E_LOCAL_MODEL_PATH is required");
  }
  test.setTimeout(mode === "hybrid-local" ? 2_400_000 : 180_000);

  const taskFixture = JSON.parse(await fs.readFile(tasksPath, "utf8")) as {
    cases: BenchmarkTask[];
  };
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), `qone-resume-${mode}-`));
  const profile = path.join(parent, "profile");
  const { app, page } = await launchDesktop(profile, mode === "hybrid-local");
  const results: CaseResult[] = [];
  let metrics = { workingSetKb: 0, cpuPercent: 0 };

  try {
    if (mode === "hybrid-local") {
      await expect
        .poll(
          () =>
            page.evaluate(async () => {
              const status = await window.qoneDesktop.modelStatus();
              return { phase: status.phase, active: status.service_active };
            }),
          { timeout: 60_000, intervals: [500, 1_000] },
        )
        .toEqual({ phase: "installed", active: true });
    }

    for (const task of taskFixture.cases) {
      const created = await api(page, "/api/goals", "POST", {
        title: task.title,
        success_criterion: task.success_criterion,
        domain: task.domain,
        priority: task.priority,
      });
      assert.equal(created.status, 201);
      const goalId = String(created.payload.id);

      await api(page, "/api/planner/refresh", "POST", {});
      const measured = await waitForPlanner(page, goalId, mode);
      const item = measured.planner.items.find(
        (candidate) => candidate.candidate_id === `goal:${goalId}`,
      );
      results.push({
        id: task.id,
        completed: Boolean(item),
        valid_goal_match: Boolean(item),
        trace_bound: Boolean(
          item &&
            item.source &&
            /^[a-f0-9]{64}$/.test(item.input_sha256 ?? "") &&
            /^[a-f0-9]{64}$/.test(item.proposal_sha256 ?? ""),
        ),
        actionable: Boolean(
          item?.first_step?.trim() && item?.done_when?.trim(),
        ),
        latency_ms: measured.latencyMs,
        configured_provider: measured.planner.provider,
        planner_status: measured.planner.status,
        effective_source: item?.source,
        item_title: item?.title,
        error: measured.planner.error ?? undefined,
      });
      metrics = await processMetrics(app);

      await api(page, `/api/goals/${goalId}`, "PATCH", { status: "paused" });
      await page.waitForTimeout(250);
    }

    const electronVersion = await app.evaluate(({ app }) => ({
      electron: process.versions.electron,
      chrome: process.versions.chrome,
      node: process.versions.node,
      application: app.getVersion(),
    }));
    const runtime: Record<string, unknown> = {
      platform: process.platform,
      arch: process.arch,
      ...electronVersion,
      sidecar_bytes: (await fs.stat(await resolveSidecar())).size,
      sidecar_sha256: await sha256File(await resolveSidecar()),
    };
    if (mode === "hybrid-local") {
      runtime.model_bytes = (await fs.stat(localModelValue!)).size;
      runtime.model_sha256 = await sha256File(localModelValue!);
    }
    const summary = summarize(mode, results, metrics, runtime);
    await fs.mkdir(benchmarkRoot, { recursive: true });
    await fs.writeFile(
      path.join(benchmarkRoot, `${mode}.json`),
      `${JSON.stringify(summary, null, 2)}\n`,
      "utf8",
    );
  } finally {
    await app.close().catch(() => undefined);
    await fs.rm(parent, { recursive: true, force: true });
  }
}

test("resume benchmark: deterministic rule recommendations", async () => {
  await runBenchmark("rules");
});

test("resume benchmark: hybrid local-model recommendations", async () => {
  await runBenchmark("hybrid-local");
});

declare global {
  interface Window {
    qoneDesktop: {
      modelStatus: () => Promise<{
        phase: string;
        service_active: boolean;
      }>;
    };
  }
}
