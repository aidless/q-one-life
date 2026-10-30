import { promises as fs } from "node:fs";
import path from "node:path";
import {
  downloadVerifiedFile,
  installedModelPath,
  ModelDownloadError,
  ModelFetch,
  QWEN_MODEL,
  verifyModelFile,
} from "./model-files";

export type ModelPhase =
  | "not_installed"
  | "checking"
  | "downloading"
  | "verifying"
  | "installed"
  | "error";

export interface ModelDescriptor {
  name: string;
  repository: string;
  revision: string;
  bytes: number;
  sha256: string;
  license: string;
}

export interface ManagedModel extends ModelDescriptor {
  url: string;
  fallbackUrls?: readonly string[];
}

export interface ModelStatus {
  phase: ModelPhase;
  installed: boolean;
  verified: boolean;
  downloading: boolean;
  received: number;
  total: number;
  error?: string;
  error_code?: string;
  model: ModelDescriptor;
}

export interface ModelManagerOptions {
  fetchImpl?: ModelFetch;
  retryDelaysMs?: readonly number[];
  onChange?: (status: ModelStatus) => void;
  model?: ManagedModel;
}

export const DEFAULT_MODEL: ManagedModel = {
  name: QWEN_MODEL.filename,
  repository: QWEN_MODEL.repository,
  revision: QWEN_MODEL.revision,
  bytes: QWEN_MODEL.bytes,
  sha256: QWEN_MODEL.sha256,
  license: QWEN_MODEL.license,
  url: QWEN_MODEL.url,
  fallbackUrls: [QWEN_MODEL.fallback_url],
};

function descriptor(model: ManagedModel): ModelDescriptor {
  return {
    name: model.name,
    repository: model.repository,
    revision: model.revision,
    bytes: model.bytes,
    sha256: model.sha256,
    license: model.license,
  };
}

function mayTryFallbackSource(error: unknown): boolean {
  if (error instanceof ModelDownloadError) {
    return new Set([
      "MODEL_DOWNLOAD_NETWORK_ERROR",
      "MODEL_DOWNLOAD_HTTP_ERROR",
      "MODEL_DOWNLOAD_EMPTY",
      "MODEL_REDIRECT_INVALID",
      "MODEL_REDIRECT_LIMIT",
      "MODEL_HOST_NOT_ALLOWED",
      "MODEL_SIZE_MISMATCH",
      "MODEL_HASH_MISMATCH",
    ]).has(error.code);
  }
  return (
    error instanceof TypeError ||
    /(?:net::ERR_|ECONNRESET|ECONNREFUSED|ETIMEDOUT|socket hang up|connection closed)/i.test(
      error instanceof Error ? error.message : String(error),
    )
  );
}

export function publicModelStatus(
  status: ModelStatus,
  serviceActive: boolean,
  serviceError?: string,
): Record<string, unknown> {
  return {
    phase: status.phase,
    installed: status.installed,
    verified: status.verified,
    downloading: status.downloading,
    received: status.received,
    total: status.total,
    error: status.error,
    error_code: status.error_code,
    model: status.model,
    service_active: serviceActive,
    service_error: serviceError,
  };
}

export class ModelManager {
  private readonly model: ManagedModel;
  private readonly options: ModelManagerOptions;
  private current: ModelStatus;
  private initializeTask: Promise<void> | undefined;
  private downloadTask: Promise<void> | undefined;
  private downloadController: AbortController | undefined;

  constructor(
    private readonly userDataDirectory: string,
    options: ModelManagerOptions = {},
  ) {
    this.options = options;
    this.model = options.model ?? DEFAULT_MODEL;
    this.current = {
      phase: "not_installed",
      installed: false,
      verified: false,
      downloading: false,
      received: 0,
      total: 0,
      model: descriptor(this.model),
    };
  }

  get filePath(): string {
    return installedModelPath(this.userDataDirectory, this.model.name);
  }

  status(): ModelStatus {
    return {
      ...this.current,
      model: { ...this.current.model },
    };
  }

  setOnChange(callback: ((status: ModelStatus) => void) | undefined): void {
    this.options.onChange = callback;
  }

  initialize(): Promise<void> {
    if (this.initializeTask) return this.initializeTask;
    this.initializeTask = this.performInitialize().finally(() => {
      this.initializeTask = undefined;
    });
    return this.initializeTask;
  }

  startDownload(): Promise<void> {
    if (this.downloadTask) return this.downloadTask;
    if (this.current.phase === "installed" && this.current.verified) {
      return Promise.resolve();
    }
    const controller = new AbortController();
    this.downloadController = controller;
    const task = this.performDownload(controller).finally(() => {
      if (this.downloadTask === task) this.downloadTask = undefined;
      if (this.downloadController === controller) this.downloadController = undefined;
    });
    this.downloadTask = task;
    return task;
  }

  cancel(): void {
    this.downloadController?.abort();
  }

  async remove(): Promise<void> {
    const active = this.downloadTask;
    this.cancel();
    if (active) await active.catch(() => undefined);
    await fs.rm(this.filePath, { force: true });
    await this.cleanupPartialFiles();
    this.update({
      phase: "not_installed",
      installed: false,
      verified: false,
      downloading: false,
      received: 0,
      total: 0,
      error: undefined,
      error_code: undefined,
    });
  }

  private update(patch: Partial<ModelStatus>): void {
    this.current = { ...this.current, ...patch, model: this.current.model };
    this.options.onChange?.(this.status());
  }

  private async performInitialize(): Promise<void> {
    await fs.mkdir(path.dirname(this.filePath), { recursive: true, mode: 0o700 });
    const exists = await fs.stat(this.filePath).then((stat) => stat.isFile()).catch(() => false);
    if (!exists) {
      this.update({
        phase: "not_installed",
        installed: false,
        verified: false,
        downloading: false,
        received: 0,
        total: 0,
        error: undefined,
        error_code: undefined,
      });
      return;
    }

    this.update({ phase: "checking", downloading: false });
    const verified = await verifyModelFile(this.filePath, this.model);
    if (!verified) {
      this.update({
        phase: "error",
        installed: false,
        verified: false,
        downloading: false,
        received: 0,
        total: this.model.bytes,
        error: "模型文件不完整或校验值不匹配，请重新下载",
        error_code: "MODEL_FILE_CORRUPT",
      });
      return;
    }
    this.update({
      phase: "installed",
      installed: true,
      verified: true,
      downloading: false,
      received: this.model.bytes,
      total: this.model.bytes,
      error: undefined,
      error_code: undefined,
    });
  }

  private async performDownload(controller: AbortController): Promise<void> {
    this.update({
      phase: "downloading",
      installed: false,
      verified: false,
      downloading: true,
      received: 0,
      total: this.model.bytes,
      error: undefined,
      error_code: undefined,
    });
    try {
      await fs.rm(this.filePath, { force: true });
      const sources = [this.model.url, ...(this.model.fallbackUrls ?? [])];
      let lastError: unknown;
      let installed = false;
      for (const [index, url] of sources.entries()) {
        try {
          await downloadVerifiedFile({
            url,
            expectedBytes: this.model.bytes,
            expectedSha256: this.model.sha256,
            destination: this.filePath,
            signal: controller.signal,
            fetchImpl: this.options.fetchImpl,
            retryDelaysMs: this.options.retryDelaysMs,
            onProgress: (progress) => {
              this.update({
                phase: progress.phase === "verifying" ? "verifying" : "downloading",
                downloading: progress.phase !== "installed",
                received: progress.received,
                total: progress.total,
              });
            },
          });
          installed = true;
          break;
        } catch (error) {
          lastError = error;
          if (
            controller.signal.aborted ||
            index === sources.length - 1 ||
            !mayTryFallbackSource(error)
          ) {
            throw error;
          }
          this.update({
            phase: "downloading",
            installed: false,
            verified: false,
            downloading: true,
            received: 0,
            total: this.model.bytes,
            error: undefined,
            error_code: undefined,
          });
        }
      }
      if (!installed) throw lastError ?? new Error("模型下载源不可用");
      this.update({
        phase: "installed",
        installed: true,
        verified: true,
        downloading: false,
        received: this.model.bytes,
        total: this.model.bytes,
        error: undefined,
        error_code: undefined,
      });
    } catch (error) {
      if (controller.signal.aborted) {
        this.update({
          phase: "not_installed",
          installed: false,
          verified: false,
          downloading: false,
          received: 0,
          total: this.model.bytes,
          error: "模型下载已取消",
          error_code: "MODEL_DOWNLOAD_CANCELLED",
        });
      } else {
        const code =
          error instanceof ModelDownloadError ? error.code : "MODEL_DOWNLOAD_FAILED";
        this.update({
          phase: "error",
          installed: false,
          verified: false,
          downloading: false,
          received: 0,
          total: this.model.bytes,
          error: error instanceof Error ? error.message : "模型下载失败",
          error_code: code,
        });
      }
      throw error;
    }
  }

  private async cleanupPartialFiles(): Promise<void> {
    const directory = path.dirname(this.filePath);
    const prefix = `${this.model.name}.`;
    let entries: string[] = [];
    try {
      entries = await fs.readdir(directory);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
      throw error;
    }
    await Promise.all(
      entries
        .filter((name) => name.startsWith(prefix) && name.endsWith(".part"))
        .map((name) => fs.rm(path.join(directory, name), { force: true })),
    );
  }
}
