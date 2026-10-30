import { randomBytes } from "node:crypto";
import {
  PreparedUpdate,
  MetadataFeed,
  prepareVerifiedUpdate,
  serveVerifiedMetadata,
  verifyArtifactFile,
  UpdateClientError,
} from "./update-client";
import {
  compareVersions,
  UpdateArch,
  UpdateChannel,
  UpdatePlatform,
} from "./update-policy";

export type UpdatePhase =
  | "unavailable"
  | "idle"
  | "checking"
  | "up_to_date"
  | "available"
  | "downloading"
  | "ready"
  | "error";

export interface UpdateStatus {
  phase: UpdatePhase;
  current_version: string;
  channel: UpdateChannel;
  available_version?: string;
  progress_percent?: number;
  transferred?: number;
  total?: number;
  can_download: boolean;
  can_install: boolean;
  manual_only: boolean;
  manual_download_url?: string;
  rollback_available: boolean;
  error_code?: string;
  retryable: boolean;
  request_id: string;
}

interface UpdateInfoLike {
  version: string;
}

interface DownloadProgressLike {
  percent?: number;
  transferred?: number;
  total?: number;
}

interface DownloadedEventLike {
  version: string;
  downloadedFile: string;
}

export interface UpdaterLike {
  autoDownload: boolean;
  autoInstallOnAppQuit: boolean;
  allowPrerelease: boolean;
  allowDowngrade: boolean;
  disableDifferentialDownload: boolean;
  channel: string | null;
  setFeedURL(options: { provider: "generic"; url: string }): void;
  checkForUpdates(): Promise<{ updateInfo: UpdateInfoLike } | null>;
  downloadUpdate(): Promise<string[]>;
  quitAndInstall(): void;
  on(event: string, listener: (...args: any[]) => void): unknown;
}

export interface UpdateControllerOptions {
  currentVersion: string;
  channel: UpdateChannel;
  platform: UpdatePlatform;
  arch: UpdateArch;
  manifestUrl: string;
  trustedKeys: Readonly<Record<string, string>>;
  updater: UpdaterLike;
  fetchImpl?: typeof fetch;
  manualOnly?: boolean;
  onStatus?: (status: UpdateStatus) => void;
}

function requestId(): string {
  return randomBytes(8).toString("hex");
}

function safeError(error: unknown): { code: string; message: string; retryable: boolean } {
  if (error instanceof UpdateClientError) {
    return {
      code: error.code,
      message: error.message,
      retryable: error.retryable,
    };
  }
  return {
    code: "UPDATE_FAILED",
    message: error instanceof Error ? error.message : "update failed",
    retryable: true,
  };
}

export class UpdateController {
  private status: UpdateStatus;
  private prepared?: PreparedUpdate;
  private feed?: MetadataFeed;
  private downloadedFile?: string;
  private pendingDownload:
    | { resolve: () => void; reject: (error: Error) => void }
    | undefined;
  private disposed = false;

  constructor(private readonly options: UpdateControllerOptions) {
    this.status = {
      phase: "idle",
      current_version: options.currentVersion,
      channel: options.channel,
      can_download: false,
      can_install: false,
      manual_only: Boolean(options.manualOnly),
      rollback_available: false,
      retryable: false,
      request_id: requestId(),
    };
    if (!Object.keys(options.trustedKeys).length) {
      this.status = {
        ...this.status,
        phase: "unavailable",
        error_code: "UPDATE_NOT_CONFIGURED",
      };
    }
    const updater = options.updater;
    updater.autoDownload = false;
    updater.autoInstallOnAppQuit = false;
    updater.on("download-progress", (progress) => {
      if (this.status.phase !== "downloading") return;
      this.emit({
        ...this.status,
        progress_percent:
          typeof progress.percent === "number"
            ? Math.max(0, Math.min(100, progress.percent))
            : this.status.progress_percent,
        transferred:
          typeof progress.transferred === "number"
            ? progress.transferred
            : this.status.transferred,
        total: typeof progress.total === "number" ? progress.total : this.status.total,
      });
    });
    updater.on("update-downloaded", (event) => {
      void this.handleDownloaded(event);
    });
    updater.on("error", (error) => {
      this.fail("UPDATE_DOWNLOAD_FAILED", error, true);
      this.pendingDownload?.reject(error);
      this.pendingDownload = undefined;
    });
  }

  publicStatus(): UpdateStatus {
    return { ...this.status };
  }

  downloadUrl(kind: "update" | "rollback" = "update"): string | undefined {
    if (kind === "rollback") {
      return this.prepared?.verified.rollback?.url;
    }
    return this.status.manual_download_url;
  }

  async check(): Promise<UpdateStatus> {
    if (this.disposed) return this.publicStatus();
    if (!Object.keys(this.options.trustedKeys).length) {
      this.emit({
        ...this.status,
        phase: "unavailable",
        can_download: false,
        can_install: false,
        error_code: "UPDATE_NOT_CONFIGURED",
        retryable: false,
        request_id: requestId(),
      });
      return this.publicStatus();
    }
    await this.closeFeed();
    this.prepared = undefined;
    this.downloadedFile = undefined;
    this.emit({
      ...this.status,
      phase: "checking",
      can_download: false,
      can_install: false,
      rollback_available: false,
      error_code: undefined,
      retryable: false,
      progress_percent: undefined,
      transferred: undefined,
      total: undefined,
      request_id: requestId(),
    });
    try {
      this.prepared = await prepareVerifiedUpdate({
        manifestUrl: this.options.manifestUrl,
        currentVersion: this.options.currentVersion,
        channel: this.options.channel,
        platform: this.options.platform,
        arch: this.options.arch,
        trustedKeys: this.options.trustedKeys,
        fetchImpl: this.options.fetchImpl,
      });
      this.feed = await serveVerifiedMetadata(
        this.prepared.verified.metadata.name,
        this.prepared.metadata,
      );
      const updater = this.options.updater;
      updater.setFeedURL({ provider: "generic", url: this.feed.url });
      updater.channel = this.options.channel;
      // electron-updater enables downgrades when a channel is assigned. The
      // manifest and the updater must both reject downgrade attempts.
      updater.allowDowngrade = false;
      updater.allowPrerelease = this.options.channel === "beta";
      updater.disableDifferentialDownload = true;
      const result = await updater.checkForUpdates();
      if (!result) {
        throw new UpdateClientError("UPDATE_UNAVAILABLE", "updater is not active", true);
      }
      if (compareVersions(result.updateInfo.version, this.prepared.verified.version) !== 0) {
        throw new UpdateClientError(
          "UPDATE_VERSION_MISMATCH",
          "signed manifest and updater metadata disagree",
        );
      }
      if (compareVersions(this.prepared.verified.version, this.options.currentVersion) <= 0) {
        this.emit({
          ...this.status,
          phase: "up_to_date",
          available_version: this.options.currentVersion,
          can_download: false,
          can_install: false,
          manual_download_url: undefined,
          error_code: undefined,
          retryable: false,
        });
      } else {
        this.emit({
          ...this.status,
          phase: "available",
          available_version: this.prepared.verified.version,
          can_download: !this.options.manualOnly,
          can_install: false,
          manual_download_url: this.options.manualOnly
            ? this.prepared.verified.artifact.url
            : undefined,
          rollback_available: Boolean(this.prepared.verified.rollback),
          error_code: undefined,
          retryable: false,
        });
      }
      return this.publicStatus();
    } catch (error) {
      await this.closeFeed();
      this.failFrom(error);
      return this.publicStatus();
    }
  }

  async download(): Promise<UpdateStatus> {
    if (
      !this.prepared ||
      !this.status.can_download ||
      this.options.manualOnly ||
      this.status.phase !== "available"
    ) {
      return this.publicStatus();
    }
    this.emit({
      ...this.status,
      phase: "downloading",
      can_download: false,
      can_install: false,
      progress_percent: 0,
      transferred: 0,
      total: this.prepared.verified.artifact.bytes,
      error_code: undefined,
      retryable: false,
      request_id: requestId(),
    });
    const completion = new Promise<void>((resolve, reject) => {
      this.pendingDownload = { resolve, reject };
    });
    try {
      await this.options.updater.downloadUpdate();
      await completion;
    } catch (error) {
      const currentPhase = this.status.phase as UpdatePhase;
      if (!this.downloadedFile && currentPhase !== "error") {
        this.failFrom(error, "UPDATE_DOWNLOAD_FAILED");
      }
    } finally {
      this.pendingDownload = undefined;
    }
    return this.publicStatus();
  }

  install(): UpdateStatus {
    if (!this.status.can_install || !this.downloadedFile) return this.publicStatus();
    this.options.updater.quitAndInstall();
    return this.publicStatus();
  }

  async dispose(): Promise<void> {
    this.disposed = true;
    await this.closeFeed();
  }

  private async handleDownloaded(event: DownloadedEventLike): Promise<void> {
    if (!this.prepared || !this.pendingDownload) return;
    try {
      if (compareVersions(event.version, this.prepared.verified.version) !== 0) {
        throw new UpdateClientError(
          "UPDATE_VERSION_MISMATCH",
          "downloaded update version does not match the signed manifest",
        );
      }
      await verifyArtifactFile(event.downloadedFile, this.prepared.verified.artifact);
      this.downloadedFile = event.downloadedFile;
      this.emit({
        ...this.status,
        phase: "ready",
        can_download: false,
        can_install: !this.options.manualOnly,
        progress_percent: 100,
        transferred: this.prepared.verified.artifact.bytes,
        total: this.prepared.verified.artifact.bytes,
        error_code: undefined,
        retryable: false,
      });
      this.pendingDownload.resolve();
      await this.closeFeed();
    } catch (error) {
      this.failFrom(error, "UPDATE_ARTIFACT_MISMATCH");
      this.pendingDownload.reject(error instanceof Error ? error : new Error(String(error)));
    }
  }

  private failFrom(error: unknown, fallback?: string): void {
    const mapped = safeError(error);
    this.fail(fallback ?? mapped.code, error, mapped.retryable);
  }

  private fail(code: string, error: unknown, retryable: boolean): void {
    const mapped = safeError(error);
    this.emit({
      ...this.status,
      phase: "error",
      can_download: false,
      can_install: false,
      error_code: code || mapped.code,
      rollback_available: Boolean(this.prepared?.verified.rollback),
      retryable,
      request_id: requestId(),
    });
  }

  private emit(status: UpdateStatus): void {
    this.status = status;
    this.options.onStatus?.(this.publicStatus());
  }

  private async closeFeed(): Promise<void> {
    const feed = this.feed;
    this.feed = undefined;
    await feed?.close().catch(() => undefined);
  }
}
