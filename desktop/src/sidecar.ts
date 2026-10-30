import { ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import http from "node:http";
import readline from "node:readline";

export interface SidecarReady {
  event: "ready";
  port: number;
  pid: number;
  version: string;
}

export interface SidecarLaunch {
  executable: string;
  args: string[];
}

export interface LocalModelHandshake {
  url: string;
  name: string;
  token: string;
}

export function sanitizeSidecarLog(line: string): string {
  return line
    .replace(
      /(authorization|x-qone-capability|x-qone-control)\s*[:=]\s*\S+/gi,
      "$1=[REDACTED]",
    )
    .replace(
      /("?(?:capability|control|cloud_key|local_model_token|token|api[_-]?key)"?\s*[:=]\s*"?)[^",\s}]+/gi,
      "$1[REDACTED]",
    )
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]")
    .slice(0, 4_000);
}

export function sidecarHandshake(
  capability: string,
  controlToken: string,
  cloudKey?: string,
  locale?: string,
  localModel?: LocalModelHandshake,
): Record<string, string> {
  return {
    capability,
    control: controlToken,
    ...(cloudKey ? { cloud_key: cloudKey } : {}),
    ...(locale ? { locale } : {}),
    ...(localModel
      ? {
          local_model_url: localModel.url,
          local_model_name: localModel.name,
          local_model_token: localModel.token,
        }
      : {}),
  };
}

export class SidecarStartError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
    this.name = "SidecarStartError";
  }
}

export class SidecarProcess {
  readonly capability = randomBytes(32).toString("base64url");
  readonly controlToken = randomBytes(32).toString("base64url");
  private child?: ChildProcessWithoutNullStreams;
  private readyValue?: SidecarReady;
  private stopping = false;

  onUnexpectedExit?: () => void;

  constructor(
    private readonly launch: SidecarLaunch,
    private readonly startupTimeoutMs = 15_000,
  ) {}

  get ready(): SidecarReady {
    if (!this.readyValue) {
      throw new Error("sidecar is not ready");
    }
    return this.readyValue;
  }

  async start(
    cloudKey?: string,
    locale?: string,
    localModel?: LocalModelHandshake,
  ): Promise<SidecarReady> {
    const child = spawn(this.launch.executable, this.launch.args, {
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
      env: { ...process.env, QONE_DESKTOP_SIDECAR: "1" },
    });
    this.child = child;
    this.stopping = false;
    child.stdin.on("error", (error) => {
      console.error(
        `[q-one-sidecar] handshake write failed: ${sanitizeSidecarLog(error.message)}`,
      );
    });
    child.stdin.write(
      `${JSON.stringify(
        sidecarHandshake(
          this.capability,
          this.controlToken,
          cloudKey,
          locale,
          localModel,
        ),
      )}\n`,
    );
    child.stdin.end();
    child.stderr.setEncoding("utf8");
    child.stderr.on("data", (chunk: string) => {
      for (const line of chunk.split(/\r?\n/)) {
        if (line.trim()) {
          console.error(`[q-one-sidecar] ${sanitizeSidecarLog(line)}`);
        }
      }
    });

    const ready = await new Promise<SidecarReady>((resolve, reject) => {
      let settled = false;
      const finish = (error?: Error, value?: SidecarReady) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (error) reject(error);
        else resolve(value as SidecarReady);
      };
      const timer = setTimeout(
        () => finish(new SidecarStartError("sidecar startup timed out", "SIDECAR_TIMEOUT")),
        this.startupTimeoutMs,
      );
      const lines = readline.createInterface({ input: child.stdout });
      lines.on("line", (line) => {
        let payload: Record<string, unknown>;
        try {
          payload = JSON.parse(line) as Record<string, unknown>;
        } catch {
          console.error("[q-one-sidecar] ignored non-handshake stdout");
          return;
        }
        if (payload.event === "error") {
          finish(
            new SidecarStartError(
              String(payload.message ?? "sidecar failed"),
              String(payload.code ?? "SIDECAR_START_FAILED"),
            ),
          );
          return;
        }
        if (
          payload.event === "ready" &&
          Number.isInteger(payload.port) &&
          Number(payload.port) > 0 &&
          Number.isInteger(payload.pid) &&
          typeof payload.version === "string"
        ) {
          finish(undefined, payload as unknown as SidecarReady);
        }
      });
      child.once("error", (error) => finish(error));
      child.once("exit", (code, signal) => {
        if (!settled) {
          finish(
            new SidecarStartError(
              `sidecar exited before ready (${code ?? signal ?? "unknown"})`,
              "SIDECAR_EXITED",
            ),
          );
        } else if (!this.stopping && this.readyValue) {
          this.onUnexpectedExit?.();
        }
      });
    });

    await this.waitForHealth(ready.port, this.capability);
    this.readyValue = ready;
    return ready;
  }

  stop(): void {
    this.stopping = true;
    if (this.child && !this.child.killed) {
      this.child.kill();
    }
  }

  async waitForExit(timeoutMs = 5_000): Promise<void> {
    const child = this.child;
    if (!child || child.exitCode !== null || child.signalCode !== null) return;
    await Promise.race([
      new Promise<void>((resolve) => child.once("exit", () => resolve())),
      new Promise<void>((resolve) => setTimeout(resolve, timeoutMs)),
    ]);
  }

  private async waitForHealth(port: number, capability: string): Promise<void> {
    let lastError: Error | undefined;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      try {
        const status = await new Promise<number>((resolve, reject) => {
          const request = http.get(
            {
              hostname: "127.0.0.1",
              port,
              path: "/api/health",
              timeout: 750,
              headers: { "X-QOne-Capability": capability },
            },
            (response) => {
              response.resume();
              resolve(response.statusCode ?? 0);
            },
          );
          request.on("timeout", () => request.destroy(new Error("health timeout")));
          request.on("error", reject);
        });
        if (status === 200) return;
        lastError = new Error(`health returned HTTP ${status}`);
      } catch (error) {
        lastError = error as Error;
      }
      await new Promise((resolve) => setTimeout(resolve, 125));
    }
    this.stop();
    throw new SidecarStartError(
      `sidecar did not become healthy: ${lastError?.message ?? "unknown"}`,
      "SIDECAR_UNHEALTHY",
    );
  }
}

export function defaultSidecarLaunch(
  dataDir: string,
  env: NodeJS.ProcessEnv = process.env,
): SidecarLaunch {
  const explicit = env.QONE_SIDECAR_BIN;
  if (explicit) {
    return { executable: explicit, args: ["--data-dir", dataDir] };
  }
  const python = env.QONE_PYTHON || "python3";
  return {
    executable: python,
    args: ["-m", "qone_life.sidecar", "--data-dir", dataDir],
  };
}
