import { _electron as electron, ElectronApplication, Page, expect, test } from "@playwright/test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

const appDirectory = path.resolve(__dirname, "..");
const sidecarValue = process.env.QONE_SIDECAR_BIN;
const localModelValue = process.env.QONE_E2E_LOCAL_MODEL_PATH;
const requireLocalModelE2E =
  process.env.QONE_REQUIRE_LOCAL_MODEL_E2E === "1";

test.beforeAll(async () => {
  if (!requireLocalModelE2E) return;
  assert.ok(sidecarValue, "QONE_SIDECAR_BIN is required in strict desktop E2E mode");
  assert.ok(
    localModelValue,
    "QONE_E2E_LOCAL_MODEL_PATH is required in strict desktop E2E mode",
  );
  const model = await fs.stat(localModelValue).catch(() => undefined);
  assert.ok(
    model?.isFile() && model.size === 639_446_688,
    "QONE_E2E_LOCAL_MODEL_PATH must point to the pinned Qwen3 Q8_0 model",
  );
});

async function resolveSidecar(): Promise<string> {
  if (!sidecarValue) {
    throw new Error("QONE_SIDECAR_BIN is required for desktop E2E");
  }
  if (path.isAbsolute(sidecarValue)) return sidecarValue;
  for (const root of [process.cwd(), appDirectory, path.resolve(appDirectory, "..")]) {
    const candidate = path.resolve(root, sidecarValue);
    if (await fs.stat(candidate).then((value) => value.isFile()).catch(() => false)) {
      return candidate;
    }
  }
  throw new Error(`QONE_SIDECAR_BIN does not point to a file: ${sidecarValue}`);
}

interface Launch {
  app: ElectronApplication;
  page: Page;
}

async function launchDesktop(profile: string): Promise<Launch> {
  const sidecar = await resolveSidecar();
  const app = await electron.launch({
    args: [
      appDirectory,
      `--user-data-dir=${profile}`,
      "--disable-gpu",
      "--disable-features=CalculateNativeWinOcclusion",
      "--enable-logging=stderr",
    ],
    env: {
      ...process.env,
      QONE_SIDECAR_BIN: sidecar,
      QONE_SKIP_MIGRATION_PROMPT: "1",
      ELECTRON_ENABLE_LOGGING: "1",
    },
  });
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");
  return { app, page };
}

async function patchOpenDialog(app: ElectronApplication, selectedPath: string): Promise<void> {
  await app.evaluate(
    ({ dialog }, value) => {
      dialog.showOpenDialog = async () => ({
        canceled: false,
        filePaths: [value],
      });
    },
    selectedPath,
  );
}

async function patchSaveDialog(app: ElectronApplication, selectedPath: string): Promise<void> {
  await app.evaluate(
    ({ dialog }, value) => {
      dialog.showSaveDialog = async () => ({
        canceled: false,
        filePath: value,
      });
    },
    selectedPath,
  );
}

async function patchRestoreConfirmation(app: ElectronApplication): Promise<void> {
  await app.evaluate(({ dialog }) => {
    dialog.showMessageBox = async () => ({
      response: 1,
      checkboxChecked: false,
    });
  });
}

async function prepareLocalModelProfile(
  profile: string,
  source: string,
): Promise<void> {
  const modelDirectory = path.join(profile, "models");
  const destination = path.join(modelDirectory, "Qwen3-0.6B-Q8_0.gguf");
  await fs.mkdir(modelDirectory, { recursive: true });
  try {
    await fs.link(source, destination);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "EEXIST") return;
    try {
      await fs.symlink(source, destination);
    } catch (symlinkError) {
      try {
        await fs.copyFile(source, destination);
      } catch (copyError) {
        throw new Error(
          `could not place the E2E model in the profile: ${String(copyError)}`,
        );
      }
    }
  }
}

async function finishOnboarding(page: Page, recoveryKey?: string): Promise<void> {
  await expect(page.locator(".step-count")).toContainText("04 / 04");
  const download = page.locator('[data-action="model-download"]');
  await expect(download).toBeVisible();
  await page.locator('[data-action="onboarding-finish"]').click();
  await expect(page.locator(".today-intro")).toBeVisible();
  if (recoveryKey) expect(recoveryKey).toMatch(/^Q1-/);
}

test("consumer onboarding, action, review, encrypted backup, restore, and relaunch", async () => {
  test.skip(!sidecarValue, "QONE_SIDECAR_BIN must point to the native sidecar");
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), "qone-e2e-"));
  const profile = path.join(parent, "profile");
  const backupDirectory = path.join(parent, "backups");
  const manualBackup = path.join(parent, "manual.qonebackup");
  const supportPackage = path.join(parent, "support.json");
  await fs.mkdir(backupDirectory, { recursive: true });

  let launched = await launchDesktop(profile);
  let { app, page } = launched;
  let recoveryKey = "";
  let closeAgain = true;

  try {
    await expect
      .poll(
        () =>
          app.evaluate(
            ({ BrowserWindow }) => BrowserWindow.getAllWindows()[0]?.isVisible() ?? false,
          ),
        { timeout: 15_000 },
      )
      .toBe(true);
    await expect(page.locator(".onboarding")).toBeVisible();

    await page.locator('[data-locale="en-US"]').click();
    await expect(page.locator(".brand-copy small")).toHaveText("Move what matters forward");
    await page.locator('[data-action="onboarding-language-next"]').click();

    await page.locator('#onboarding-goal-form [name="title"]').fill("Ship a small desktop release");
    await page
      .locator('#onboarding-goal-form [name="success_criterion"]')
      .fill("A clean machine can install and complete the full local flow");
    await page.locator('#onboarding-goal-form button[type="submit"]').click();
    await expect(page.locator(".step-count")).toContainText("03 / 04");

    const backupStatus = await page.evaluate(() => window.qoneDesktop.backupStatus());
    if (backupStatus.persistent) {
      await patchOpenDialog(app, backupDirectory);
      await page.locator('[data-action="backup-choose-directory"]').click();
      const keyField = page.locator("#backup-recovery-key");
      await expect(keyField).toBeVisible();
      await expect(page.locator(".recovery-qr svg")).toBeVisible();
      recoveryKey = await keyField.inputValue();
      await page.locator("#backup-key-confirmed").check();
      await page.locator('[data-action="onboarding-enable-backup"]').click();
    } else {
      await patchSaveDialog(app, manualBackup);
      await page.locator('[data-action="backup-now"]').click();
      const keyField = page.locator("#consumer-dialog #backup-recovery-key");
      await expect(keyField).toBeVisible();
      await expect(page.locator("#consumer-dialog .recovery-qr svg")).toBeVisible();
      recoveryKey = await keyField.inputValue();
      await page.locator('[data-action="close-dialog"]').click();
      await page.locator('.button.primary[data-action="onboarding-next-model"]').click();
    }
    await finishOnboarding(page, recoveryKey);

    const recommendation = page.locator(".recommendation-card");
    if (!(await recommendation.isVisible().catch(() => false))) {
      await page.locator('[data-action="refresh-planner"]').click();
    }
    await expect(recommendation).toBeVisible();
    await recommendation.locator('[data-action="accept-suggestion"]').click();
    const task = page.locator('input[data-task-id]').first();
    await expect(task).toBeVisible();
    await task.check();
    await expect(task).toBeChecked();

    await page.locator('[data-route="review"]').click();
    await page.locator('#review-form textarea[name="text"]').fill(
      "The first local flow is complete; keep the weekly review and verify backup recovery.",
    );
    await page.locator('#review-form button[type="submit"]').click();
    await expect(
      page.getByText(
        "The first local flow is complete; keep the weekly review and verify backup recovery.",
      ),
    ).toBeVisible();

    await page.locator('[data-route="settings"]').click();
    await patchSaveDialog(app, manualBackup);
    await page.locator('[data-action="backup-now"]').click();
    const backupKeyField = page.locator("#consumer-dialog #backup-recovery-key");
    await expect(backupKeyField).toBeVisible();
    await expect(page.locator("#consumer-dialog .recovery-qr svg")).toBeVisible();
    const savedRecoveryKey = await backupKeyField.inputValue();
    await page.locator('[data-action="close-dialog"]').click();

    await page.locator('[data-route="goals"]').click();
    await page.locator('[data-action="show-goal-form"]').first().click();
    await page.locator('#goal-form [name="title"]').fill("Post-backup disposable goal");
    await page
      .locator('#goal-form [name="success_criterion"]')
      .fill("This goal must disappear after restoring the earlier backup");
    await page.locator('#goal-form button[type="submit"]').click();
    await expect(page.getByText("Post-backup disposable goal")).toBeVisible();

    await page.locator('[data-route="settings"]').click();
    await patchOpenDialog(app, manualBackup);
    await patchRestoreConfirmation(app);
    await page.locator('[data-action="backup-inspect"]').click();
    await page.locator('#restore-key-form textarea[name="recovery_key"]').fill(savedRecoveryKey);
    await page.locator('#restore-key-form button[type="submit"]').click();
    await expect(page.locator(".today-intro")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Ship a small desktop release").first()).toBeVisible();
    await expect(page.getByText("Post-backup disposable goal")).toHaveCount(0);

    await app.close();
    closeAgain = false;
    launched = await launchDesktop(profile);
    ({ app, page } = launched);
    closeAgain = true;
    await expect(page.locator(".today-intro")).toBeVisible();
    await expect(page.getByText("Ship a small desktop release").first()).toBeVisible();
    await expect(page.getByText("Post-backup disposable goal")).toHaveCount(0);
    await page.locator('[data-route="review"]').click();
    await expect(page.getByText("The first local flow is complete")).toBeVisible();

    await page.locator('[data-route="settings"]').click();
    await patchSaveDialog(app, supportPackage);
    await page.locator('[data-action="support-preview"]').click();
    await expect(
      page.locator("#consumer-dialog .support-preview"),
    ).toContainText('"schema": "q-one-support-v1"');
    await page
      .locator('#consumer-dialog [data-action="support-export"]')
      .click();
    await expect(page.locator("#toast")).toContainText("Support package saved");
    const support = JSON.parse(await fs.readFile(supportPackage, "utf8")) as {
      privacy: Record<string, boolean>;
      runtime: Record<string, unknown>;
    };
    assert.deepEqual(support.privacy, {
      includes_personal_records: false,
      includes_working_database: false,
      includes_absolute_paths: false,
      includes_secrets: false,
    });
    assert.doesNotMatch(JSON.stringify(support), /Ship a small desktop release/);
    assert.doesNotMatch(JSON.stringify(support), /manual\.qonebackup/);
  } finally {
    if (closeAgain) await app.close().catch(() => undefined);
    await fs.rm(parent, { recursive: true, force: true });
  }
});

test("built-in local model produces a grounded sidecar recommendation", async () => {
  test.skip(
    !sidecarValue || !localModelValue,
    "QONE_SIDECAR_BIN and QONE_E2E_LOCAL_MODEL_PATH are required",
  );
  test.setTimeout(420_000);
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), "qone-local-e2e-"));
  const profile = path.join(parent, "profile");
  await prepareLocalModelProfile(profile, localModelValue!);

  let app: ElectronApplication | undefined;
  try {
    const launched = await launchDesktop(profile);
    ({ app } = launched);
    const { page } = launched;
    await expect(page.locator(".onboarding")).toBeVisible();

    await expect
      .poll(
        () =>
          page.evaluate(async () => {
            const status = await window.qoneDesktop.modelStatus();
            return {
              phase: status.phase,
              serviceActive: status.service_active,
            };
          }),
        { timeout: 60_000, intervals: [250, 500, 1_000] },
      )
      .toEqual({ phase: "installed", serviceActive: true });

    await page.locator('[data-locale="en-US"]').click();
    await page.locator('[data-action="onboarding-language-next"]').click();
    await page.locator('#onboarding-goal-form [name="title"]').fill(
      "Draft the first page of a personal project README",
    );
    await page
      .locator('#onboarding-goal-form [name="success_criterion"]')
      .fill(
        "README.md states the project purpose, local setup, and one command that was actually run",
      );
    await page.locator('#onboarding-goal-form button[type="submit"]').click();
    await expect(page.locator(".step-count")).toContainText("03 / 04");
    await page.locator('[data-action="onboarding-next-model"]').first().click();
    await expect(page.locator(".model-ready-card")).toBeVisible();
    await page.locator('[data-action="onboarding-finish"]').click();
    await expect(page.locator(".today-intro")).toBeVisible();

    await expect
      .poll(
        () =>
          page.evaluate(async () => {
            const response = await fetch("/api/planner");
            const planner = await response.json();
            return {
              provider: planner.provider,
              status: planner.status,
              itemCount: planner.items?.length ?? 0,
            };
          }),
        { timeout: 300_000, intervals: [1_000, 2_000, 5_000] },
      )
      .toMatchObject({ provider: "local", status: "ready", itemCount: 1 });

    const runtime = await page.evaluate(async () => {
      const [plannerResponse, bootstrapResponse] = await Promise.all([
        fetch("/api/planner"),
        fetch("/api/bootstrap?days=7"),
      ]);
      return {
        planner: await plannerResponse.json(),
        bootstrap: await bootstrapResponse.json(),
      };
    });
    assert.match(runtime.planner.items[0].source, /^local:/);
    assert.match(runtime.planner.items[0].first_step, /\S/);
    assert.match(runtime.planner.items[0].done_when, /\S/);
    const localRun = runtime.bootstrap.runs.find(
      (run: Record<string, unknown>) =>
        run.provider === "local" && run.status === "completed",
    );
    assert.ok(localRun, "no completed local model run was recorded");
    assert.equal(localRun.usage.local, true);
    assert.match(String(localRun.usage.input_sha256), /^[a-f0-9]{64}$/);

    const recommendation = page.locator(".recommendation-card");
    await expect(recommendation).toBeVisible();
    await expect(recommendation).toContainText("Local model");
    await expect(recommendation).toContainText("Start here");
    await expect(recommendation).toContainText("Stop when this is true");
  } finally {
    await app?.close().catch(() => undefined);
    await fs.rm(parent, { recursive: true, force: true });
  }
});

declare global {
  interface Window {
    qoneDesktop: {
      backupStatus: () => Promise<{ persistent: boolean }>;
      modelStatus: () => Promise<{
        phase: string;
        service_active: boolean;
      }>;
    };
  }
}
