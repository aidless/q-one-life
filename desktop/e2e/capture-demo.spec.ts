import { _electron as electron, expect, test } from "@playwright/test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

const appDirectory = path.resolve(__dirname, "..");
const captureEnabled = process.env.QONE_CAPTURE_DEMO === "1";
const sidecarValue = process.env.QONE_SIDECAR_BIN;
const localModelValue = process.env.QONE_E2E_LOCAL_MODEL_PATH;
const outputDirectory = path.resolve(
  process.env.QONE_DEMO_OUTPUT ??
    path.join(appDirectory, "..", "artifacts", "resume-kit", "demo"),
);

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

test("capture the verified consumer demo storyboard", async () => {
  test.skip(!captureEnabled, "set QONE_CAPTURE_DEMO=1 to capture screenshots");
  test.skip(!sidecarValue, "QONE_SIDECAR_BIN is required");
  test.setTimeout(420_000);

  const parent = await fs.mkdtemp(path.join(os.tmpdir(), "qone-demo-capture-"));
  const profile = path.join(parent, "profile");
  if (localModelValue) {
    await prepareLocalModelProfile(profile, localModelValue);
  }
  await fs.mkdir(outputDirectory, { recursive: true });
  const app = await electron.launch({
    args: [
      appDirectory,
      `--user-data-dir=${profile}`,
      "--disable-gpu",
      "--disable-features=CalculateNativeWinOcclusion",
    ],
    env: {
      ...process.env,
      QONE_SIDECAR_BIN: path.isAbsolute(sidecarValue!)
        ? sidecarValue!
        : path.resolve(appDirectory, sidecarValue!),
      QONE_SKIP_MIGRATION_PROMPT: "1",
    },
  });
  const page = await app.firstWindow();

  try {
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator(".onboarding")).toBeVisible();
    await page.locator('[data-locale="zh-CN"]').click();
    await page.screenshot({
      path: path.join(outputDirectory, "01-first-run.png"),
      animations: "disabled",
    });
    await page.locator('[data-action="onboarding-language-next"]').click();
    await page
      .locator('#onboarding-goal-form [name="title"]')
      .fill("完成 Q-One 简历演示与可复现验收");
    await page
      .locator('#onboarding-goal-form [name="success_criterion"]')
      .fill("三分钟演示、固定任务评测和证据回执均可复现，且不夸大发布状态");
    await page.locator('#onboarding-goal-form button[type="submit"]').click();
    await expect(page.locator(".step-count")).toContainText("03 / 04");
    await page.locator('[data-action="onboarding-next-model"]').first().click();
    if (localModelValue) {
      await expect(page.locator(".model-ready-card")).toBeVisible({
        timeout: 60_000,
      });
    }
    await expect(page.locator(".step-count")).toContainText("04 / 04");
    await page.locator('[data-action="onboarding-finish"]').click();
    await expect(page.locator(".today-intro")).toBeVisible();

    const recommendation = page.locator(".recommendation-card");
    await expect(recommendation).toBeVisible({ timeout: 300_000 });
    if (localModelValue) {
      await expect(recommendation).toContainText("本地模型", {
        timeout: 300_000,
      });
    }
    await page.screenshot({
      path: path.join(outputDirectory, "02-today-recommendation.png"),
      animations: "disabled",
      fullPage: true,
    });

    await recommendation.locator('[data-action="accept-suggestion"]').click();
    const task = page.locator('input[data-task-id]').first();
    await expect(task).toBeVisible();
    await task.check();
    await expect(task).toBeChecked();
    await page.screenshot({
      path: path.join(outputDirectory, "03-completed-action.png"),
      animations: "disabled",
      fullPage: true,
    });

    await page.locator('[data-route="review"]').click();
    await page
      .locator('#review-form textarea[name="text"]')
      .fill("已完成本地推荐、行动和证据回执；下一步继续验证恢复与公开发布门。");
    await page.locator('#review-form button[type="submit"]').click();
    await expect(page.getByText("已完成本地推荐、行动和证据回执")).toBeVisible();
    await page.screenshot({
      path: path.join(outputDirectory, "04-review.png"),
      animations: "disabled",
      fullPage: true,
    });

    await page.locator('[data-route="settings"]').click();
    await page.screenshot({
      path: path.join(outputDirectory, "05-settings-backup.png"),
      animations: "disabled",
      fullPage: true,
    });

    const files = await fs.readdir(outputDirectory);
    assert.ok(files.includes("01-first-run.png"));
    assert.ok(files.includes("02-today-recommendation.png"));
    assert.ok(files.includes("03-completed-action.png"));
    assert.ok(files.includes("04-review.png"));
    assert.ok(files.includes("05-settings-backup.png"));
  } finally {
    await app.close().catch(() => undefined);
    await fs.rm(parent, { recursive: true, force: true });
  }
});
