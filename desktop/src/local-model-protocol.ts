import http from "node:http";
import { timingSafeEqual } from "node:crypto";

export interface ChatMessage {
  role: string;
  content: string;
}

export interface LocalGenerationRequest {
  messages: ChatMessage[];
  maxTokens: number;
  temperature: number;
  responseSchema?: Record<string, unknown>;
  signal: AbortSignal;
}

export interface LocalGenerationResult {
  text: string;
  promptTokens: number;
  completionTokens: number;
}

export type LocalGenerator = (
  request: LocalGenerationRequest,
) => Promise<LocalGenerationResult>;

export interface LocalModelServerOptions {
  token: string;
  modelName: string;
  generator: LocalGenerator;
  modelState?: () => Record<string, unknown>;
}

const MAX_BODY_BYTES = 1024 * 1024;

function tokenMatches(supplied: string, expected: string): boolean {
  const left = Buffer.from(supplied);
  const right = Buffer.from(`Bearer ${expected}`);
  return left.length === right.length && timingSafeEqual(left, right);
}

function json(
  response: http.ServerResponse,
  status: number,
  payload: unknown,
): void {
  const encoded = Buffer.from(JSON.stringify(payload));
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": String(encoded.length),
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  response.end(encoded);
}

function errorPayload(
  message: string,
  code: string,
  type = "invalid_request_error",
) {
  return { error: { message, code, type } };
}

async function readJsonBody(request: http.IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    const value = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += value.length;
    if (size > MAX_BODY_BYTES) {
      throw Object.assign(new Error("request too large"), {
        code: "REQUEST_TOO_LARGE",
      });
    }
    chunks.push(value);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw Object.assign(new Error("invalid json"), {
      code: "INVALID_JSON",
    });
  }
}

function parseRequest(raw: unknown): Omit<LocalGenerationRequest, "signal"> {
  if (!raw || typeof raw !== "object") {
    throw Object.assign(new Error("body must be an object"), {
      code: "INVALID_REQUEST",
    });
  }
  const body = raw as Record<string, unknown>;
  if (!Array.isArray(body.messages) || !body.messages.length) {
    throw Object.assign(new Error("messages are required"), {
      code: "INVALID_REQUEST",
    });
  }
  const messages: ChatMessage[] = [];
  for (const item of body.messages) {
    if (
      !item ||
      typeof item !== "object" ||
      typeof (item as Record<string, unknown>).role !== "string" ||
      typeof (item as Record<string, unknown>).content !== "string" ||
      ((item as Record<string, unknown>).content as string).length > 256 * 1024
    ) {
      throw Object.assign(new Error("message shape is invalid"), {
        code: "INVALID_REQUEST",
      });
    }
    messages.push({
      role: (item as Record<string, string>).role,
      content: (item as Record<string, string>).content,
    });
  }
  const maxTokens =
    body.max_tokens === undefined ? 900 : Number(body.max_tokens);
  if (!Number.isInteger(maxTokens) || maxTokens < 1 || maxTokens > 4096) {
    throw Object.assign(new Error("max_tokens is invalid"), {
      code: "INVALID_REQUEST",
    });
  }
  const temperature =
    body.temperature === undefined ? 0 : Number(body.temperature);
  if (
    !Number.isFinite(temperature) ||
    temperature < 0 ||
    temperature > 2
  ) {
    throw Object.assign(new Error("temperature is invalid"), {
      code: "INVALID_REQUEST",
    });
  }
  let responseSchema: Record<string, unknown> | undefined;
  if (body.response_format && typeof body.response_format === "object") {
    const format = body.response_format as Record<string, unknown>;
    const schema = format.json_schema;
    if (schema && typeof schema === "object") {
      const candidate = (schema as Record<string, unknown>).schema;
      if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) {
        responseSchema = candidate as Record<string, unknown>;
      }
    } else if (format.type === "json_object") {
      responseSchema = { type: "object", additionalProperties: true };
    }
  }
  return { messages, maxTokens, temperature, responseSchema };
}

export function createLocalModelServer(
  options: LocalModelServerOptions,
): http.Server {
  if (options.token.length < 32) {
    throw new Error("local model access token is too short");
  }
  const server = http.createServer(async (request, response) => {
    if (!tokenMatches(request.headers.authorization ?? "", options.token)) {
      json(
        response,
        401,
        errorPayload("local model authentication required", "AUTH_REQUIRED"),
      );
      return;
    }
    if (request.method === "GET" && request.url === "/health") {
      json(response, 200, {
        status: "ok",
        model: options.modelName,
        ...(options.modelState?.() ?? {}),
      });
      return;
    }
    if (request.method === "GET" && request.url === "/v1/models") {
      json(response, 200, {
        object: "list",
        data: [
          {
            id: options.modelName,
            object: "model",
            owned_by: "local",
          },
        ],
      });
      return;
    }
    if (
      request.method !== "POST" ||
      request.url !== "/v1/chat/completions"
    ) {
      json(
        response,
        404,
        errorPayload("endpoint not found", "NOT_FOUND"),
      );
      return;
    }
    if (!request.headers["content-type"]?.includes("application/json")) {
      json(
        response,
        415,
        errorPayload("JSON content type required", "CONTENT_TYPE_REQUIRED"),
      );
      return;
    }

    const abort = new AbortController();
    response.once("close", () => {
      if (!response.writableEnded) abort.abort();
    });
    try {
      const parsed = parseRequest(await readJsonBody(request));
      const result = await options.generator({ ...parsed, signal: abort.signal });
      if (abort.signal.aborted) return;
      json(response, 200, {
        id: `chatcmpl-local-${Date.now()}`,
        object: "chat.completion",
        created: Math.floor(Date.now() / 1000),
        model: options.modelName,
        choices: [
          {
            index: 0,
            message: { role: "assistant", content: result.text },
            finish_reason: "stop",
          },
        ],
        usage: {
          prompt_tokens: result.promptTokens,
          completion_tokens: result.completionTokens,
          total_tokens: result.promptTokens + result.completionTokens,
        },
      });
    } catch (error) {
      const code =
        typeof (error as { code?: unknown }).code === "string"
          ? (error as { code: string }).code
          : "LOCAL_MODEL_FAILED";
      const status =
        code === "INVALID_JSON" || code === "INVALID_REQUEST"
          ? 400
          : code === "REQUEST_TOO_LARGE"
            ? 413
            : 503;
      json(
        response,
        status,
        errorPayload(
          status === 503
            ? "local model could not complete the request"
            : "invalid local model request",
          code,
          status === 503 ? "server_error" : "invalid_request_error",
        ),
      );
    }
  });
  server.requestTimeout = 150_000;
  server.headersTimeout = 10_000;
  return server;
}
