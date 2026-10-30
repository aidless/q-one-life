import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  Menu,
  safeStorage,
  session,
  shell,
} from "electron";
import { autoUpdater } from "electron-updater";
import { randomBytes } from "node:crypto";
import { promises as fs } from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import {
  effectiveAutomaticBackup,
  pruneAutomaticBackups,
} from "./backup-files";
import {
  configureModelFetchSession,
  createElectronModelFetch,
} from "./electron-model-fetch";
import { LocalModelHost } from "./local-model";
import { directoryIsEmpty, legacyDataPath, migrateLegacyData } from "./migration";
import { ModelManager, ModelStatus, publicModelStatus } from "./model-manager";
import { proxyRulesFromEnvironment } from "./model-network";
import { createProxyModelFetch } from "./proxy-model-fetch";
import { recoveryKeyQrSvg } from "./recovery-qr";
import { SecretStore, SecretStoreStatus } from "./secure-store";
import {
  defaultSidecarLaunch,
  LocalModelHandshake,
  SidecarProcess,
  SidecarReady,
} from "./sidecar";
import {
  buildSupportPackage,
  redactSupportText,
  SupportEvent,
} from "./support";
import { loadTrustedUpdateKeys } from "./update-client";
import { UpdateController, UpdaterLike } from "./update-controller";
import {
  channelForVersion,
  linuxUpdateRequiresManualInstall,
  UpdatePlatform,
} from "./update-policy";

let mainWindow: BrowserWindow | undefined;
let sidecar: SidecarProcess | undefined;
let dataDirectory: string | undefined;
let secretStore: SecretStore | undefined;
let cloudKey: string | undefined;
let activePort = 0;
let activeCapability = "";
let quitting = false;
let restarting = false;
let restartCount = 0;
let pendingRestorePath: string | undefined;
let backupTimer: NodeJS.Timeout | undefined;
let updateTimer: NodeJS.Timeout | undefined;
let modelManager: ModelManager | undefined;
const localModelHost = new LocalModelHost();
let localModelError: string | undefined;
let modelActivation: Promise<boolean> | undefined;
let modelStatusBroadcastTimer: NodeJS.Timeout | undefined;
let modelFetchDisposer: (() => Promise<void>) | undefined;
const supportEvents: SupportEvent[] = [];
let updateController: UpdateController | undefined;

app.setName("Q-One");

function resourcesSidecar(): string {
  const executable = process.platform === "win32" ? "qone-life-sidecar.exe" : "qone-life-sidecar";
  return path.join(process.resourcesPath, "sidecar", executable);
}

function sidecarLaunch(directory: string) {
  if (!app.isPackaged) return defaultSidecarLaunch(directory);
  return { executable: resourcesSidecar(), args: ["--data-dir", directory] };
}

function redactLog(value: string): string {
  return value
    .replace(/(authorization|x-qone-capability|x-qone-control)\s*[:=]\s*\S+/gi, "$1=[REDACTED]")
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]")
    .replace(/(cloud_key|capability|control)\s*["']?\s*[:=]\s*["']?[^,\s"']+/gi, "$1=[REDACTED]")
    .replace(/\b(?:sk|qone|key)[-_][A-Za-z0-9_-]{16,}\b/g, "[REDACTED]");
}

function redactError(error: unknown): string {
  return redactLog(error instanceof Error ? error.message : String(error));
}

function recordSupportEvent(kind: string, message: unknown): void {
  supportEvents.push({
    at: new Date().toISOString(),
    kind,
    message: redactSupportText(message instanceof Error ? message.message : String(message)),
  });
  if (supportEvents.length > 100) supportEvents.splice(0, supportEvents.length - 100);
}

interface BackupSettings {
  version: 1;
  directory?: string;
  enabled: boolean;
  last_backup_at?: string;
  recovery_key_confirmed_at?: string;
}

function backupSettingsPath(): string {
  return path.join(app.getPath("userData"), "backup-settings.json");
}

async function readBackupSettings(): Promise<BackupSettings> {
  try {
    const raw = JSON.parse(await fs.readFile(backupSettingsPath(), "utf8")) as Partial<BackupSettings>;
    const confirmedAt =
      typeof raw.recovery_key_confirmed_at === "string"
        ? raw.recovery_key_confirmed_at
        : undefined;
    return {
      version: 1,
      directory: typeof raw.directory === "string" ? raw.directory : undefined,
      enabled: raw.enabled === true && Boolean(confirmedAt),
      last_backup_at: typeof raw.last_backup_at === "string" ? raw.last_backup_at : undefined,
      recovery_key_confirmed_at: confirmedAt,
    };
  } catch {
    return { version: 1, enabled: false };
  }
}

async function writeBackupSettings(settings: BackupSettings): Promise<void> {
  const file = backupSettingsPath();
  await fs.mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    await fs.writeFile(temporary, JSON.stringify(settings), { mode: 0o600 });
    await fs.rename(temporary, file);
  } finally {
    await fs.rm(temporary, { force: true }).catch(() => undefined);
  }
}

function sidecarRequest<T>(
  method: "GET" | "POST",
  requestPath: string,
  body?: Record<string, unknown>,
): Promise<T> {
  return new Promise((resolve, reject) => {
    if (!sidecar || !activePort) {
      reject(new Error("本地服务尚未就绪"));
      return;
    }
    const encoded = body === undefined ? undefined : JSON.stringify(body);
    const headers: Record<string, string> = {
      "X-QOne-Client": "web",
      "X-QOne-Capability": sidecar.capability,
    };
    if (requestPath.startsWith("/api/desktop/")) {
      headers["X-QOne-Control"] = sidecar.controlToken;
    }
    if (encoded !== undefined) {
      headers["Content-Type"] = "application/json";
      headers["Content-Length"] = String(Buffer.byteLength(encoded));
    }
    const request = http.request(
      {
        hostname: "127.0.0.1",
        port: activePort,
        path: requestPath,
        method,
        timeout: 45_000,
        headers,
      },
      (response) => {
        const chunks: Buffer[] = [];
        response.on("data", (chunk: Buffer) => chunks.push(chunk));
        response.on("end", () => {
          const text = Buffer.concat(chunks).toString("utf8");
          if ((response.statusCode ?? 500) >= 400) {
            let message = `本地服务返回 HTTP ${response.statusCode}`;
            try {
              const parsed = JSON.parse(text) as { detail?: string; error?: { code?: string } };
              message = parsed.detail || parsed.error?.code || message;
            } catch {
              // Do not include an untrusted response body in the error.
            }
            reject(new Error(redactLog(message)));
            return;
          }
          try {
            resolve(JSON.parse(text) as T);
          } catch {
            reject(new Error("本地服务返回了无效响应"));
          }
        });
      },
    );
    request.on("timeout", () => request.destroy(new Error("本地服务请求超时")));
    request.on("error", (error) => reject(error));
    if (encoded !== undefined) request.write(encoded);
    request.end();
  });
}

async function writeAtomicFile(file: string, contents: Buffer): Promise<void> {
  await fs.mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.${process.pid}.tmp`;
  let handle: Awaited<ReturnType<typeof fs.open>> | undefined;
  try {
    handle = await fs.open(temporary, "w", 0o600);
    await handle.writeFile(contents);
    await handle.sync();
    await handle.close();
    handle = undefined;
    try {
      await fs.rename(temporary, file);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
      await fs.rm(file, { force: true });
      await fs.rename(temporary, file);
    }
    if (process.platform !== "win32") {
      const directory = await fs.open(path.dirname(file), "r");
      try {
        await directory.sync();
      } finally {
        await directory.close();
      }
    }
  } finally {
    await handle?.close().catch(() => undefined);
    await fs.rm(temporary, { force: true }).catch(() => undefined);
  }
}

async function ensureBackupKeys(): Promise<{ dataKey: string; recoveryKey: string }> {
  if (!secretStore) throw new Error("系统密钥存储尚未初始化");
  let dataKey = await secretStore.get("backup_data_key");
  let recoveryKey = await secretStore.get("backup_recovery_key");
  if (!dataKey) {
    dataKey = randomBytes(32).toString("base64");
    await secretStore.set("backup_data_key", dataKey);
  }
  if (!recoveryKey) {
    recoveryKey = randomBytes(32).toString("base64");
    await secretStore.set("backup_recovery_key", recoveryKey);
  }
  return { dataKey, recoveryKey };
}

async function formatRecoveryKey(rawBase64: string): Promise<string> {
  const result = await sidecarRequest<{ recovery_key: string }>(
    "POST",
    "/api/desktop/backup/recovery-key",
    { key: rawBase64 },
  );
  return result.recovery_key;
}

async function createBackupTo(file: string): Promise<{ path: string; recoveryKey: string }> {
  const keys = await ensureBackupKeys();
  const container = await sidecarRequest<Record<string, unknown>>(
    "POST",
    "/api/desktop/backup/export",
    { data_key: keys.dataKey, recovery_key: keys.recoveryKey },
  );
  await writeAtomicFile(file, Buffer.from(`${JSON.stringify(container)}\n`, "utf8"));
  const settings = await readBackupSettings();
  settings.last_backup_at = new Date().toISOString();
  await writeBackupSettings(settings);
  return { path: file, recoveryKey: await formatRecoveryKey(keys.recoveryKey) };
}

function recoveryKeyDisplay(recoveryKey: string): {
  recoveryKey: string;
  recoveryKeyQr: string;
} {
  return {
    recoveryKey,
    recoveryKeyQr: recoveryKeyQrSvg(recoveryKey),
  };
}

function maintenanceLaunch(directory: string) {
  const common = ["restore", "--data-dir", directory, "--backup-stdin", "--replace"];
  if (app.isPackaged) {
    return { executable: resourcesSidecar(), args: common };
  }
  if (process.env.QONE_SIDECAR_BIN) {
    return { executable: process.env.QONE_SIDECAR_BIN, args: common };
  }
  return {
    executable: process.env.QONE_PYTHON || "python3",
    args: ["-m", "qone_life.sidecar", ...common],
  };
}

async function runMaintenanceRestore(raw: Record<string, unknown>): Promise<Record<string, unknown>> {
  if (!dataDirectory) throw new Error("数据目录尚未初始化");
  const launch = maintenanceLaunch(dataDirectory);
  return new Promise((resolve, reject) => {
    const child = spawn(launch.executable, launch.args, {
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
      env: process.env,
    });
    const stdout: Buffer[] = [];
    const stderr: Buffer[] = [];
    const timer = setTimeout(() => child.kill(), 60_000);
    child.stdout.on("data", (chunk: Buffer) => stdout.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => stderr.push(chunk));
    child.once("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.once("exit", (code) => {
      clearTimeout(timer);
      const output = Buffer.concat(stdout).toString("utf8").trim();
      if (code !== 0) {
        let message = "恢复进程未完成";
        try {
          const parsed = JSON.parse(output) as { error?: string };
          message = parsed.error || message;
        } catch {
          const diagnostic = Buffer.concat(stderr).toString("utf8").trim();
          if (diagnostic) message = redactLog(diagnostic);
        }
        reject(new Error(message));
        return;
      }
      try {
        resolve(JSON.parse(output) as Record<string, unknown>);
      } catch {
        reject(new Error("恢复进程返回了无效响应"));
      }
    });
    child.stdin.end(JSON.stringify(raw));
  });
}

async function chooseDataDirectory(): Promise<string | undefined> {
  const directory = path.join(app.getPath("userData"), "data");
  await fs.mkdir(directory, { recursive: true, mode: 0o700 });
  if (!(await directoryIsEmpty(directory))) return directory;

  const source = legacyDataPath(os.homedir());
  try {
    const stat = await fs.stat(source);
    if (!stat.isDirectory() || (await fs.readdir(source)).length === 0) return directory;
  } catch {
    return directory;
  }

  const ignoredMarker = path.join(app.getPath("userData"), ".legacy-import-declined");
  if (await fs.stat(ignoredMarker).then(() => true).catch(() => false)) return directory;
  if (process.env.QONE_SKIP_MIGRATION_PROMPT === "1") return directory;

  const choice = await dialog.showMessageBox({
    type: "question",
    title: "Q-One",
    message: "发现旧版 Q-One 本地数据",
    detail:
      "可以将数据复制到桌面版的新空间。原目录会保留；迁移前请关闭旧版网页程序。",
    buttons: ["迁移并继续", "使用新空间", "退出"],
    defaultId: 0,
    cancelId: 2,
    noLink: true,
  });
  if (choice.response === 2) return undefined;
  if (choice.response === 1) {
    await fs.writeFile(ignoredMarker, new Date().toISOString(), { mode: 0o600 });
    return directory;
  }

  try {
    await fs.rmdir(directory);
    await migrateLegacyData(source, directory);
    return directory;
  } catch (error) {
    await dialog.showMessageBox({
      type: "error",
      title: "迁移未完成",
      message: "旧数据没有被删除",
      detail: redactError(error),
      buttons: ["退出"],
    });
    return undefined;
  }
}

async function migratePlaintextCloudKey(directory: string, store: SecretStore): Promise<void> {
  const settingsPath = path.join(directory, "settings.json");
  try {
    const raw = JSON.parse(await fs.readFile(settingsPath, "utf8")) as Record<string, unknown>;
    if (typeof raw.cloud_key !== "string" || !raw.cloud_key) return;
    await store.set("cloud_key", raw.cloud_key);
    delete raw.cloud_key;
    const temporary = `${settingsPath}.${process.pid}.migrate`;
    await fs.writeFile(temporary, JSON.stringify(raw), { mode: 0o600 });
    await fs.rename(temporary, settingsPath);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
      console.error(`[q-one] settings migration skipped: ${redactError(error)}`);
    }
  }
}

function hardenSession(appSession: Electron.Session): void {
  appSession.webRequest.onBeforeSendHeaders(
    { urls: ["<all_urls>"] },
    (details, callback) => {
      try {
        const url = new URL(details.url);
        if (
          url.hostname === "127.0.0.1" &&
          url.port === String(activePort) &&
          url.pathname.startsWith("/api/") &&
          activeCapability
        ) {
          details.requestHeaders["X-QOne-Capability"] = activeCapability;
        }
      } catch {
        // The sidecar rejects malformed URLs; never attach a secret blindly.
      }
      callback({ requestHeaders: details.requestHeaders });
    },
  );
}

function hardenWindow(window: BrowserWindow): void {
  window.webContents.on("will-navigate", (event, url) => {
    if (url.startsWith("data:text/html")) return;
    try {
      if (!activePort || new URL(url).origin !== `http://127.0.0.1:${activePort}`) {
        event.preventDefault();
      }
    } catch {
      event.preventDefault();
    }
  });
  window.webContents.on("will-attach-webview", (event) => event.preventDefault());
  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
}

function revealWindow(): void {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  if (!mainWindow.isVisible()) mainWindow.show();
  mainWindow.focus();
}

function errorPage(message: string): string {
  const safeMessage = message
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  return `data:text/html;charset=utf-8,${encodeURIComponent(
    `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Q-One 无法启动</title>` +
      `<style>body{font:16px/1.6 sans-serif;max-width:680px;margin:12vh auto;padding:24px;color:#183b35}` +
      `h1{font-size:28px}code{background:#eef2ed;padding:3px 6px;border-radius:4px}</style>` +
      `<h1>为什么没有打开？</h1><p>本地数据服务没有完成启动。你的原数据没有被删除。</p>` +
      `<p>${safeMessage}</p><p>请先退出其他 Q-One 实例后重试；如果问题持续，请导出脱敏支持包并联系维护者。</p></html>`,
  )}`;
}

async function showRuntimeError(message: string): Promise<void> {
  recordSupportEvent("runtime-error", message);
  if (mainWindow) {
    await mainWindow.loadURL(errorPage(message));
    return;
  }
  await dialog.showMessageBox({
    type: "error",
    title: "Q-One 无法启动",
    message: "本地服务未能启动",
    detail: message,
    buttons: ["退出"],
  });
  app.quit();
}

async function waitFor(
  condition: () => boolean,
  timeoutMs: number,
  description: string,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (condition()) return;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`timed out waiting for ${description}`);
}

function modelStatusPayload(): Record<string, unknown> {
  const status: ModelStatus =
    modelManager?.status() ?? {
      phase: "not_installed",
      installed: false,
      verified: false,
      downloading: false,
      received: 0,
      total: 0,
      model: {
        name: "Qwen3-0.6B-Q8_0.gguf",
        repository: "Qwen/Qwen3-0.6B-GGUF",
        revision: "23749fefcc72300e3a2ad315e1317431b06b590a",
        bytes: 639446688,
        sha256: "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031",
        license: "Apache-2.0",
      },
    };
  return publicModelStatus(
    status,
    Boolean(localModelHost.endpoint),
    localModelError,
  );
}

function broadcastModelStatus(): void {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send("qone:model-status", modelStatusPayload());
}

function scheduleModelStatusBroadcast(): void {
  if (modelStatusBroadcastTimer) return;
  modelStatusBroadcastTimer = setTimeout(() => {
    modelStatusBroadcastTimer = undefined;
    broadcastModelStatus();
  }, 150);
}

function localModelHandshake(): LocalModelHandshake | undefined {
  const endpoint = localModelHost.endpoint;
  if (!endpoint || modelManager?.status().phase !== "installed") return undefined;
  return { url: endpoint.baseUrl, name: endpoint.model, token: endpoint.token };
}

async function activateLocalModel(restart: boolean): Promise<boolean> {
  if (!modelManager || localModelHost.endpoint) return Boolean(localModelHost.endpoint);
  if (modelManager.status().phase !== "installed") return false;
  if (modelActivation) return modelActivation;
  modelActivation = (async () => {
    try {
      await localModelHost.start(
        modelManager!.filePath,
        path.join(__dirname, "model-service.js"),
      );
      localModelError = undefined;
    } catch (error) {
      localModelError = "LOCAL_MODEL_SERVICE_FAILED";
      recordSupportEvent("local-model-start", error);
      console.error(`[q-one] local model service unavailable: ${redactError(error)}`);
      broadcastModelStatus();
      return false;
    } finally {
      modelActivation = undefined;
    }
    broadcastModelStatus();
    if (restart && sidecar) {
      await restartSidecar();
    }
    return true;
  })();
  return modelActivation;
}

async function startSidecar(directory: string): Promise<SidecarReady> {
  const processSidecar = new SidecarProcess(sidecarLaunch(directory));
  processSidecar.onUnexpectedExit = () => {
    void handleUnexpectedExit(processSidecar);
  };
  try {
    const ready = await processSidecar.start(
      cloudKey,
      app.getLocale(),
      localModelHandshake(),
    );
    sidecar = processSidecar;
    activePort = ready.port;
    activeCapability = processSidecar.capability;
    return ready;
  } catch (error) {
    recordSupportEvent("sidecar-start", error);
    processSidecar.stop();
    await processSidecar.waitForExit();
    throw error;
  }
}

async function restartSidecar(): Promise<void> {
  if (!dataDirectory || restarting) return;
  restarting = true;
  try {
    const previous = sidecar;
    sidecar = undefined;
    previous?.stop();
    await previous?.waitForExit();
    const ready = await startSidecar(dataDirectory);
    if (mainWindow) await mainWindow.loadURL(`http://127.0.0.1:${ready.port}`);
  } finally {
    restarting = false;
  }
}

async function handleUnexpectedExit(processSidecar: SidecarProcess): Promise<void> {
  if (quitting || restarting || sidecar !== processSidecar || !dataDirectory) return;
  recordSupportEvent("sidecar-exit", "local sidecar exited unexpectedly");
  sidecar = undefined;
  if (restartCount >= 2) {
    await showRuntimeError("本地服务连续退出两次，已停止自动重启。请导出支持包后再试。");
    return;
  }
  restartCount += 1;
  try {
    const ready = await startSidecar(dataDirectory);
    if (mainWindow) await mainWindow.loadURL(`http://127.0.0.1:${ready.port}`);
  } catch (error) {
    await showRuntimeError(`本地服务重启失败：${redactError(error)}`);
  }
}

async function runCrashRecoverySmoke(): Promise<void> {
  for (let crash = 1; crash <= 2; crash += 1) {
    const current = sidecar;
    if (!current) throw new Error(`sidecar missing before crash ${crash}`);
    const previousPort = activePort;
    process.kill(current.ready.pid, "SIGKILL");
    await waitFor(
      () =>
        sidecar !== undefined &&
        sidecar !== current &&
        activePort !== previousPort,
      30_000,
      `sidecar restart ${crash}`,
    );
  }
  const current = sidecar;
  if (!current) throw new Error("sidecar missing before final crash");
  process.kill(current.ready.pid, "SIGKILL");
  await waitFor(
    () => Boolean(mainWindow?.webContents.getURL().startsWith("data:text/html")),
    30_000,
    "recoverable error page",
  );
  console.log(
    `QONE_CRASH_SMOKE_OK ${JSON.stringify({
      restarts: restartCount,
      title: mainWindow ? await mainWindow.webContents.executeJavaScript("document.title") : "",
    })}`,
  );
}

async function runLocalModelHostSmoke(): Promise<void> {
  const explicitModelPath = process.env.QONE_MODEL_SMOKE_PATH;
  const folder = explicitModelPath
    ? undefined
    : await fs.mkdtemp(path.join(app.getPath("temp"), "qone-model-host-"));
  const modelPath = explicitModelPath || path.join(folder!, "placeholder.gguf");
  if (!explicitModelPath) {
    await fs.writeFile(modelPath, Buffer.from("not loaded during host smoke"));
  }
  try {
    const endpoint = await localModelHost.start(
      modelPath,
      path.join(__dirname, "model-service.js"),
    );
    const healthUrl = new URL(endpoint.baseUrl);
    healthUrl.pathname = "/health";
    const response = await fetch(healthUrl, {
      headers: { Authorization: `Bearer ${endpoint.token}` },
    });
    if (!response.ok) {
      throw new Error(`local model host health returned HTTP ${response.status}`);
    }
    const health = (await response.json()) as Record<string, unknown>;
    let inference: Record<string, unknown> | undefined;
    if (explicitModelPath) {
      const completion = await fetch(`${endpoint.baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${endpoint.token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: endpoint.model,
          messages: [
            {
              role: "system",
              content: "Return only JSON with the requested field. Do not explain.",
            },
            {
              role: "user",
              content: 'Return {"answer":"yes"}.',
            },
          ],
          max_tokens: 96,
          temperature: 0,
          response_format: {
            type: "json_schema",
            json_schema: {
              name: "smoke",
              strict: true,
              schema: {
                type: "object",
                properties: { answer: { type: "string", enum: ["yes"] } },
                required: ["answer"],
                additionalProperties: false,
              },
            },
          },
        }),
      });
      if (!completion.ok) {
        const detail = await completion.text();
        throw new Error(`local inference returned HTTP ${completion.status}: ${detail.slice(0, 500)}`);
      }
      const payload = (await completion.json()) as Record<string, any>;
      const content = payload?.choices?.[0]?.message?.content;
      const parsed = typeof content === "string" ? JSON.parse(content) : undefined;
      if (parsed?.answer !== "yes") throw new Error("local inference returned invalid JSON");
      inference = {
        answer: parsed.answer,
        usage: payload.usage,
      };
    }
    console.log(
      `QONE_MODEL_HOST_SMOKE_OK ${JSON.stringify({
        status: health.status,
        model: health.model,
        loopback: healthUrl.hostname === "127.0.0.1",
        ...(inference ? { inference } : {}),
      })}`,
    );
  } finally {
    localModelHost.stop();
    if (folder) await fs.rm(folder, { recursive: true, force: true });
  }
}

async function secretStatus(): Promise<SecretStoreStatus> {
  return (
    (await secretStore?.status()) ?? {
      available: false,
      backend: "unavailable",
      persistent: false,
    }
  );
}

async function supportSnapshot(): Promise<Record<string, unknown>> {
  const secrets = await secretStatus();
  const settings = await readBackupSettings();
  const recoveryKeyAvailable = Boolean(
    await secretStore?.get("backup_recovery_key"),
  );
  const backup = effectiveAutomaticBackup(
    settings.enabled,
    secrets.persistent,
    recoveryKeyAvailable,
  );
  return buildSupportPackage({
    application: {
      version: app.getVersion(),
      packaged: app.isPackaged,
      electron: process.versions.electron ?? "unknown",
      chrome: process.versions.chrome ?? "unknown",
      node: process.versions.node,
    },
    system: {
      platform: process.platform,
      release: os.release(),
      arch: process.arch,
      locale: app.getLocale(),
    },
    runtime: {
      secret_store: secrets,
      cloud_key_set: Boolean(cloudKey),
      sidecar: sidecar
        ? { ready: true, version: sidecar.ready.version, pid: sidecar.ready.pid }
        : { ready: false },
      local_model: modelStatusPayload(),
      backup: {
        enabled: backup.enabled,
        paused: backup.paused,
        pause_reason: backup.pauseReason,
        configured: Boolean(settings.directory),
        recovery_key_confirmed: Boolean(settings.recovery_key_confirmed_at),
        recovery_key_available: recoveryKeyAvailable,
        last_backup_at: settings.last_backup_at,
      },
      restart_count: restartCount,
    },
    events: supportEvents,
  });
}

function beginModelDownload(): void {
  const manager = modelManager;
  if (!manager) throw new Error("模型管理器尚未初始化");
  void (async () => {
    try {
      await manager.startDownload();
      if (manager.status().phase === "installed") {
        const activated = await activateLocalModel(false);
        if (activated && sidecar) await restartSidecar();
      }
    } catch (error) {
      const code = (error as { code?: unknown }).code;
      if (code !== "MODEL_DOWNLOAD_CANCELLED") {
        console.error(`[q-one] model download stopped: ${redactError(error)}`);
        if (manager.status().phase === "installed") {
          await showRuntimeError(`本地模型已安装，但服务切换失败：${redactError(error)}`);
        }
      }
    }
  })();
}

function updateManifestBase(): string {
  const configured = process.env.QONE_UPDATE_MANIFEST_BASE;
  if (!app.isPackaged && configured) return configured.replace(/\/+$/, "");
  return "https://aidless.github.io/q-one-life/updates";
}

async function updatePublicKeys(): Promise<Record<string, string>> {
  const file = app.isPackaged
    ? path.join(process.resourcesPath, "update-public-keys.json")
    : path.resolve(__dirname, "..", "update-public-keys.json");
  try {
    return await loadTrustedUpdateKeys(file);
  } catch (error) {
    recordSupportEvent("update-key-load", error);
    return {};
  }
}

async function linuxPackageType(): Promise<string | undefined> {
  if (process.platform !== "linux") return undefined;
  try {
    return (await fs.readFile(path.join(process.resourcesPath, "package-type"), "utf8")).trim();
  } catch {
    return undefined;
  }
}

async function initializeUpdateController(): Promise<void> {
  const keys = await updatePublicKeys();
  const channel = channelForVersion(app.getVersion());
  const platform = process.platform;
  if (!["darwin", "linux", "win32"].includes(platform)) return;
  const arch = process.arch === "arm64" ? "arm64" : "x64";
  const updateSession = session.fromPartition("persist:q-one-updates");
  const manifestUrl = `${updateManifestBase()}/${channel}/manifest.json`;
  const packageType = await linuxPackageType();
  updateController = new UpdateController({
    currentVersion: app.getVersion(),
    channel,
    platform: platform as UpdatePlatform,
    arch,
    manifestUrl,
    trustedKeys: keys,
    updater: autoUpdater as unknown as UpdaterLike,
    fetchImpl: updateSession.fetch.bind(updateSession) as typeof fetch,
    manualOnly:
      platform === "linux" &&
      linuxUpdateRequiresManualInstall(packageType, process.env.APPIMAGE),
    onStatus: (status) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("qone:update-status", status);
      }
    },
  });
}

function registerIpc(): void {
  ipcMain.handle("qone:runtime-info", async () => ({
    version: app.getVersion(),
    packaged: app.isPackaged,
    dataDir: dataDirectory,
    secret: await secretStatus(),
  }));
  ipcMain.handle("qone:model-status", async () => modelStatusPayload());
  ipcMain.handle("qone:model-download", async () => {
    beginModelDownload();
    return modelStatusPayload();
  });
  ipcMain.handle("qone:model-cancel", async () => {
    modelManager?.cancel();
    return modelStatusPayload();
  });
  ipcMain.handle("qone:model-remove", async () => {
    if (!modelManager) throw new Error("模型管理器尚未初始化");
    localModelHost.stop();
    await modelManager.remove();
    localModelError = undefined;
    if (sidecar) await restartSidecar();
    return modelStatusPayload();
  });
  ipcMain.handle("qone:support-preview", async () => supportSnapshot());
  ipcMain.handle("qone:support-export", async () => {
    const result = await dialog.showSaveDialog({
      title: "导出 Q-One 支持包",
      defaultPath: path.join(
        app.getPath("documents"),
        `Q-One-support-${new Date().toISOString().replace(/[:.]/g, "-")}.json`,
      ),
      filters: [{ name: "Q-One support package", extensions: ["json"] }],
    });
    if (result.canceled || !result.filePath) return { canceled: true };
    const support = await supportSnapshot();
    await writeAtomicFile(
      result.filePath,
      Buffer.from(`${JSON.stringify(support, null, 2)}\n`, "utf8"),
    );
    return { canceled: false, path: result.filePath };
  });
  ipcMain.handle("qone:update-status", async () => updateController?.publicStatus());
  ipcMain.handle("qone:update-check", async () => updateController?.check());
  ipcMain.handle("qone:update-download", async () => updateController?.download());
  ipcMain.handle("qone:update-install", async () => updateController?.install());
  ipcMain.handle("qone:update-open-download", async (_event, rawKind: unknown) => {
    const kind = rawKind === undefined ? "update" : rawKind;
    if (kind !== "update" && kind !== "rollback") {
      throw new Error("更新下载类型无效");
    }
    const url = updateController?.downloadUrl(kind);
    if (!url) throw new Error("没有可用的手动更新下载地址");
    await shell.openExternal(url);
    return { opened: true };
  });
  ipcMain.handle("qone:secret-status", async () => ({
    ...(await secretStatus()),
    cloud_key_set: Boolean(cloudKey),
  }));
  ipcMain.handle("qone:set-cloud-key", async (_event, value: unknown) => {
    if (!secretStore || typeof value !== "string" || value.length > 8192) {
      throw new Error("接口密钥格式无效");
    }
    const trimmed = value.trim();
    await secretStore.set("cloud_key", trimmed);
    cloudKey = trimmed || undefined;
    await restartSidecar();
    return { ...(await secretStatus()), cloud_key_set: Boolean(cloudKey) };
  });
  ipcMain.handle("qone:clear-cloud-key", async () => {
    if (!secretStore) throw new Error("系统密钥存储尚未初始化");
    await secretStore.delete("cloud_key");
    cloudKey = undefined;
    await restartSidecar();
    return { ...(await secretStatus()), cloud_key_set: false };
  });
  ipcMain.handle("qone:backup-status", async () => {
    const settings = await readBackupSettings();
    const secrets = await secretStatus();
    const recoveryKeyAvailable = Boolean(
      await secretStore?.get("backup_recovery_key"),
    );
    const effective = effectiveAutomaticBackup(
      settings.enabled,
      secrets.persistent,
      recoveryKeyAvailable,
    );
    return {
      ...secrets,
      directory: settings.directory,
      enabled: effective.enabled,
      configured_enabled: settings.enabled,
      paused: effective.paused,
      pause_reason: effective.pauseReason,
      automatic_available: secrets.persistent,
      last_backup_at: settings.last_backup_at,
      recovery_key_confirmed: Boolean(settings.recovery_key_confirmed_at),
      recovery_key_available: recoveryKeyAvailable,
    };
  });
  ipcMain.handle("qone:backup-choose-directory", async () => {
    if (!secretStore) throw new Error("系统密钥存储尚未初始化");
    if (!(await secretStore.status()).persistent) {
      throw new Error("系统密钥存储不能安全持久化自动备份密钥，请使用手动加密备份");
    }
    const result = await dialog.showOpenDialog({
      title: "选择自动备份目录",
      properties: ["openDirectory", "createDirectory"],
    });
    if (result.canceled || !result.filePaths[0]) return { canceled: true };
    const settings = await readBackupSettings();
    settings.directory = result.filePaths[0];
    settings.enabled = false;
    settings.recovery_key_confirmed_at = undefined;
    await writeBackupSettings(settings);
    const keys = await ensureBackupKeys();
    return {
      canceled: false,
      directory: settings.directory,
      ...recoveryKeyDisplay(await formatRecoveryKey(keys.recoveryKey)),
    };
  });
  ipcMain.handle("qone:backup-set-enabled", async (_event, enabled: unknown) => {
    if (typeof enabled !== "boolean") throw new Error("备份开关无效");
    if (enabled && !(await secretStatus()).persistent) {
      throw new Error("系统密钥存储不能安全持久化自动备份密钥");
    }
    const settings = await readBackupSettings();
    if (enabled && (!settings.directory || !settings.recovery_key_confirmed_at)) {
      throw new Error("请先选择目录并确认已保存恢复密钥");
    }
    settings.enabled = enabled;
    await writeBackupSettings(settings);
    return settings;
  });
  ipcMain.handle("qone:backup-enable-auto", async (_event, confirmed: unknown) => {
    if (confirmed !== true) throw new Error("请先确认已保存恢复密钥");
    if (!secretStore) throw new Error("系统密钥存储尚未初始化");
    if (!(await secretStore.status()).persistent) {
      throw new Error("系统密钥存储不能安全持久化自动备份密钥");
    }
    const settings = await readBackupSettings();
    if (!settings.directory) throw new Error("请先选择自动备份目录");
    await ensureBackupKeys();
    settings.enabled = true;
    settings.recovery_key_confirmed_at = new Date().toISOString();
    await writeBackupSettings(settings);
    return settings;
  });
  ipcMain.handle("qone:backup-now", async () => {
    const settings = await readBackupSettings();
    if (!settings.directory) {
      const result = await dialog.showSaveDialog({
        title: "保存 Q-One 加密备份",
        defaultPath: path.join(
          app.getPath("documents"),
          `Q-One-backup-${new Date().toISOString().slice(0, 10)}.qonebackup`,
        ),
        filters: [{ name: "Q-One encrypted backup", extensions: ["qonebackup"] }],
      });
      if (result.canceled || !result.filePath) return { canceled: true };
      const created = await createBackupTo(result.filePath);
      return {
        canceled: false,
        ...created,
        recoveryKeyQr: recoveryKeyQrSvg(created.recoveryKey),
      };
    }
    const file = path.join(
      settings.directory,
      `Q-One-backup-${new Date().toISOString().slice(0, 10)}.qonebackup`,
    );
    const created = await createBackupTo(file);
    return {
      canceled: false,
      ...created,
      recoveryKeyQr: recoveryKeyQrSvg(created.recoveryKey),
    };
  });
  ipcMain.handle("qone:backup-inspect", async () => {
    const result = await dialog.showOpenDialog({
      title: "检查 Q-One 加密备份",
      properties: ["openFile"],
      filters: [{ name: "Q-One encrypted backup", extensions: ["qonebackup"] }],
    });
    if (result.canceled || !result.filePaths[0]) return { canceled: true };
    const file = result.filePaths[0];
    try {
      const container = JSON.parse(await fs.readFile(file, "utf8")) as Record<string, unknown>;
      const metadata = await sidecarRequest("POST", "/api/desktop/backup/inspect", container);
      pendingRestorePath = file;
      return { canceled: false, path: file, metadata };
    } catch {
      throw new Error("备份文件无法识别或已损坏");
    }
  });
  ipcMain.handle("qone:backup-restore", async (_event, recoveryKeyText: unknown) => {
    if (!pendingRestorePath || typeof recoveryKeyText !== "string") {
      throw new Error("请先选择备份并填写恢复密钥");
    }
    const container = JSON.parse(await fs.readFile(pendingRestorePath, "utf8")) as Record<string, unknown>;
    const raw = await sidecarRequest<Record<string, unknown>>(
      "POST",
      "/api/desktop/backup/decrypt",
      { container, recovery_key_text: recoveryKeyText.trim() },
    );
    const confirmation = await dialog.showMessageBox({
      type: "warning",
      title: "恢复会替换当前数据",
      message: "恢复前会保留一份本地安全副本",
      detail: "恢复完成后，当前 Q-One 数据会被备份中的数据替换。请确认恢复密钥来自可信位置。",
      buttons: ["取消", "替换并恢复"],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
    });
    if (confirmation.response !== 1) return { canceled: true };
    const previous = sidecar;
    sidecar = undefined;
    previous?.stop();
    await previous?.waitForExit();
    try {
      const result = await runMaintenanceRestore(raw);
      const ready = await startSidecar(dataDirectory!);
      if (mainWindow) await mainWindow.loadURL(`http://127.0.0.1:${ready.port}`);
      pendingRestorePath = undefined;
      return { canceled: false, ...result };
    } catch (error) {
      const ready = await startSidecar(dataDirectory!);
      if (mainWindow) await mainWindow.loadURL(`http://127.0.0.1:${ready.port}`);
      throw error;
    }
  });
}

async function autoBackupTick(): Promise<void> {
  if (!secretStore || !sidecar || process.env.QONE_SMOKE_TEST === "1") return;
  if (!(await secretStore.status()).persistent) return;
  const settings = await readBackupSettings();
  if (!settings.enabled || !settings.directory || !settings.recovery_key_confirmed_at) {
    return;
  }
  const last = settings.last_backup_at ? Date.parse(settings.last_backup_at) : 0;
  if (Number.isFinite(last) && Date.now() - last < 24 * 60 * 60 * 1000) return;
  if (!(await secretStore.get("backup_recovery_key"))) return;
  try {
    await createBackupTo(
      path.join(
        settings.directory,
        `Q-One-autosave-${new Date().toISOString().slice(0, 10)}.qonebackup`,
      ),
    );
    await pruneAutomaticBackups(settings.directory);
  } catch (error) {
    console.error(`[q-one] automatic backup skipped: ${redactError(error)}`);
  }
}

async function boot(): Promise<void> {
  dataDirectory = await chooseDataDirectory();
  if (!dataDirectory) {
    app.quit();
    return;
  }
  if (!secretStore) throw new Error("secret store is unavailable");
  await migratePlaintextCloudKey(dataDirectory, secretStore);
  cloudKey = await secretStore.get("cloud_key");
  if (modelManager) {
    await modelManager.initialize();
    if (modelManager.status().phase === "installed") {
      await activateLocalModel(false);
    }
  }

  let ready: SidecarReady;
  try {
    ready = await startSidecar(dataDirectory);
  } catch (error) {
    await showRuntimeError(redactError(error));
    return;
  }

  const appSession = session.fromPartition("persist:q-one");
  hardenSession(appSession);
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 900,
    minWidth: 820,
    minHeight: 620,
    backgroundColor: "#f5f4f0",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      session: appSession,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      devTools: !app.isPackaged || process.env.QONE_DEVTOOLS === "1",
    },
  });
  hardenWindow(mainWindow);
  mainWindow.once("ready-to-show", revealWindow);
  mainWindow.webContents.on("render-process-gone", (_event, details) => {
    recordSupportEvent(
      "renderer-exit",
      `renderer exited: ${details.reason} (${details.exitCode})`,
    );
  });
  mainWindow.webContents.on("unresponsive", () => {
    recordSupportEvent("renderer-unresponsive", "renderer became unresponsive");
  });
  mainWindow.webContents.on(
    "did-fail-load",
    (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
      if (isMainFrame) {
        recordSupportEvent(
          "page-load-failed",
          `${errorCode} ${errorDescription} ${validatedURL}`,
        );
      }
    },
  );
  mainWindow.on("closed", () => {
    mainWindow = undefined;
  });
  await mainWindow.loadURL(`http://127.0.0.1:${ready.port}`);
  // Some Linux window managers do not emit ready-to-show consistently. The
  // loaded UI must still become interactive instead of remaining hidden.
  revealWindow();
  if (process.env.QONE_CRASH_SMOKE_TEST === "1") {
    try {
      await runCrashRecoverySmoke();
    } catch (error) {
      console.error(`QONE_CRASH_SMOKE_FAILED ${redactError(error)}`);
      process.exitCode = 1;
    }
    app.quit();
    return;
  }
  if (process.env.QONE_SMOKE_TEST === "1") {
    try {
      const health = await mainWindow.webContents.executeJavaScript(
        "fetch('/api/health').then(async response => ({status: response.status, body: await response.json()}))",
      );
      console.log(
        `QONE_SMOKE_OK ${JSON.stringify({
          title: await mainWindow.webContents.executeJavaScript("document.title"),
          health,
          secrets: await secretStatus(),
        })}`,
      );
    } catch (error) {
      console.error(`QONE_SMOKE_FAILED ${redactError(error)}`);
      process.exitCode = 1;
    }
    app.quit();
    return;
  }
  if (!app.isPackaged && process.env.QONE_DEVTOOLS === "1") {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }
  void autoBackupTick();
  backupTimer = setInterval(() => void autoBackupTick(), 6 * 60 * 60 * 1000);
  if (!process.env.QONE_SMOKE_TEST && !process.env.QONE_CRASH_SMOKE_TEST) {
    void updateController?.check();
    updateTimer = setInterval(
      () => void updateController?.check(),
      24 * 60 * 60 * 1000,
    );
  }
}

const hasLock = app.requestSingleInstanceLock();
if (!hasLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
  app.on("before-quit", () => {
    quitting = true;
    if (backupTimer) clearInterval(backupTimer);
    if (updateTimer) clearInterval(updateTimer);
    if (modelStatusBroadcastTimer) clearTimeout(modelStatusBroadcastTimer);
    void updateController?.dispose();
    void modelFetchDisposer?.();
    localModelHost.stop();
    sidecar?.stop();
  });
  app.whenReady().then(async () => {
    Menu.setApplicationMenu(null);
    secretStore = new SecretStore(
      path.join(app.getPath("userData"), "secrets.json"),
      safeStorage,
    );
    const modelNetworkSession = session.fromPartition("q-one-model-download");
    const environmentProxy = proxyRulesFromEnvironment(process.env);
    const explicitProxyFetch =
      environmentProxy && /^https?:/i.test(environmentProxy)
        ? createProxyModelFetch(environmentProxy)
        : undefined;
    if (explicitProxyFetch) {
      modelFetchDisposer = explicitProxyFetch.close;
    } else {
      await configureModelFetchSession(modelNetworkSession);
    }
    modelManager = new ModelManager(app.getPath("userData"), {
      fetchImpl:
        explicitProxyFetch?.fetchImpl ??
        createElectronModelFetch(modelNetworkSession),
      onChange: scheduleModelStatusBroadcast,
    });
    localModelHost.onUnexpectedExit = () => {
      localModelError = "LOCAL_MODEL_SERVICE_EXITED";
      scheduleModelStatusBroadcast();
    };
    if (process.env.QONE_MODEL_HOST_SMOKE_TEST === "1") {
      try {
        await runLocalModelHostSmoke();
      } catch (error) {
        console.error(`QONE_MODEL_HOST_SMOKE_FAILED ${redactError(error)}`);
        process.exitCode = 1;
      }
      app.quit();
      return;
    }
    registerIpc();
    await initializeUpdateController();
    try {
      await boot();
    } catch (error) {
      await showRuntimeError(redactError(error));
    }
  });
  app.on("window-all-closed", () => app.quit());
}
