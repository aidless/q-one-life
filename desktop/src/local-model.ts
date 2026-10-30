import { utilityProcess, UtilityProcess } from "electron";
import { promises as fs } from "node:fs";

export interface LocalModelEndpoint {
  baseUrl: string;
  model: string;
  token: string;
}

interface ReadyMessage {
  type: "ready";
  port: number;
  pid: number;
  token: string;
  model: string;
}

interface ErrorMessage {
  type: "error";
  code: string;
  message: string;
}

export class LocalModelStartError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
    this.name = "LocalModelStartError";
  }
}

function isReadyMessage(value: unknown): value is ReadyMessage {
  if (!value || typeof value !== "object") return false;
  const message = value as Record<string, unknown>;
  return (
    message.type === "ready" &&
    Number.isInteger(message.port) &&
    Number(message.port) > 0 &&
    Number(message.port) <= 65_535 &&
    Number.isInteger(message.pid) &&
    typeof message.token === "string" &&
    message.token.length >= 32 &&
    typeof message.model === "string" &&
    message.model.length > 0
  );
}

function isErrorMessage(value: unknown): value is ErrorMessage {
  if (!value || typeof value !== "object") return false;
  const message = value as Record<string, unknown>;
  return (
    message.type === "error" &&
    typeof message.code === "string" &&
    typeof message.message === "string"
  );
}

function sanitizeLog(line: string): string {
  return line
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]")
    .replace(/(authorization|token|api[_-]?key)\s*[:=]\s*\S+/gi, "$1=[REDACTED]")
    .slice(0, 4_000);
}

export class LocalModelHost {
  private child: UtilityProcess | undefined;
  private endpointValue: LocalModelEndpoint | undefined;
  private stopping = false;

  onUnexpectedExit?: (code: number) => void;

  get endpoint(): LocalModelEndpoint | undefined {
    return this.endpointValue;
  }

  async start(modelPath: string, serviceScript: string): Promise<LocalModelEndpoint> {
    this.stop();
    const stat = await fs.stat(modelPath).catch(() => undefined);
    if (!stat?.isFile() || stat.size <= 0) {
      throw new LocalModelStartError("本地模型文件不存在", "LOCAL_MODEL_FILE_MISSING");
    }

    const child = utilityProcess.fork(serviceScript, [], {
      serviceName: "Q-One Local Model",
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        QONE_MODEL_PATH: modelPath,
      } as Record<string, string>,
    });
    this.child = child;
    this.stopping = false;
    child.stdout?.setEncoding("utf8");
    child.stderr?.setEncoding("utf8");
    child.stdout?.on("data", (chunk: string) => {
      const line = sanitizeLog(String(chunk).trim());
      if (line) console.log(`[q-one-model] ${line}`);
    });
    child.stderr?.on("data", (chunk: string) => {
      const line = sanitizeLog(String(chunk).trim());
      if (line) console.error(`[q-one-model] ${line}`);
    });

    const endpoint = await new Promise<LocalModelEndpoint>((resolve, reject) => {
      let settled = false;
      const finish = (error?: Error, value?: LocalModelEndpoint) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (error) reject(error);
        else resolve(value as LocalModelEndpoint);
      };
      const timer = setTimeout(
        () => finish(new LocalModelStartError("本地模型服务启动超时", "LOCAL_MODEL_TIMEOUT")),
        30_000,
      );
      child.on("message", (message: unknown) => {
        if (isReadyMessage(message)) {
          finish(undefined, {
            baseUrl: `http://127.0.0.1:${message.port}/v1`,
            model: message.model,
            token: message.token,
          });
        } else if (isErrorMessage(message)) {
          finish(new LocalModelStartError(message.message, message.code));
        }
      });
      child.once("error", (_type, location, report) => {
        const detail = report || location || "utility process error";
        finish(
          new LocalModelStartError(
            sanitizeLog(String(detail)),
            "LOCAL_MODEL_PROCESS_ERROR",
          ),
        );
      });
      child.once("exit", (code) => {
        if (!settled) {
          finish(
            new LocalModelStartError(
              `本地模型服务在就绪前退出（${code}）`,
              "LOCAL_MODEL_PROCESS_EXITED",
            ),
          );
        } else if (!this.stopping && this.child === child) {
          this.endpointValue = undefined;
          this.child = undefined;
          this.onUnexpectedExit?.(code);
        }
      });
    });

    if (this.child !== child || this.stopping) {
      child.kill();
      throw new LocalModelStartError("本地模型服务启动被取消", "LOCAL_MODEL_CANCELLED");
    }
    this.endpointValue = endpoint;
    return endpoint;
  }

  stop(): void {
    this.stopping = true;
    this.endpointValue = undefined;
    const child = this.child;
    this.child = undefined;
    if (!child) return;
    try {
      child.postMessage({ type: "shutdown" });
    } catch {
      // The process may already be gone.
    }
    const timer = setTimeout(() => child.kill(), 750);
    timer.unref();
  }
}
