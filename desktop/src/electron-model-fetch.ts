import { net, Session } from "electron";
import { Readable } from "node:stream";
import {
  DEFAULT_ALLOWED_HOSTS,
  ModelDownloadError,
  ModelFetch,
  validateModelDownloadUrl,
} from "./model-files";
import {
  NetworkEnvironment,
  proxyRulesFromEnvironment,
} from "./model-network";

const MAX_REDIRECTS = 5;

export async function configureModelFetchSession(
  networkSession: Session,
  env: NetworkEnvironment = process.env,
): Promise<boolean> {
  const proxyRules = proxyRulesFromEnvironment(env);
  if (!proxyRules) return false;
  await networkSession.setProxy({
    mode: "fixed_servers",
    proxyRules,
    proxyBypassRules: "<local>",
  });
  return true;
}

function networkFailure(): ModelDownloadError {
  return new ModelDownloadError(
    "模型下载网络连接中断",
    "MODEL_DOWNLOAD_NETWORK_ERROR",
    true,
  );
}

function responseHeaders(
  values: Record<string, string | string[]>,
): Headers {
  const headers = new Headers();
  for (const [name, value] of Object.entries(values)) {
    headers.set(name, Array.isArray(value) ? value.join(", ") : value);
  }
  return headers;
}

/**
 * Use Chromium's network stack so system proxy settings are respected while
 * retaining exact, per-hop redirect validation. Electron's fetch() cannot
 * expose manual redirect responses, so net.request() is the narrow bridge.
 */
export function createElectronModelFetch(
  networkSession: Session,
  allowedHosts: readonly string[] = DEFAULT_ALLOWED_HOSTS,
): ModelFetch {
  return (input, init = {}) =>
    new Promise<Response>((resolve, reject) => {
      const initialUrl = input instanceof URL ? input : new URL(input);
      try {
        validateModelDownloadUrl(initialUrl, allowedHosts);
      } catch (error) {
        reject(error);
        return;
      }

      let settled = false;
      let redirects = 0;
      let policyError: ModelDownloadError | undefined;
      const headers = new Headers(init.headers);
      if (!headers.has("Accept")) headers.set("Accept", "application/octet-stream");

      const request = net.request({
        url: initialUrl.href,
        session: networkSession,
        method: init.method ?? "GET",
        redirect: "manual",
        headers: Object.fromEntries(headers.entries()),
        credentials: "omit",
        useSessionCookies: false,
        cache: "no-store",
      });

      const cleanupSignal = () => {
        init.signal?.removeEventListener("abort", abort);
      };
      const failBeforeResponse = (error: unknown) => {
        if (settled) return;
        settled = true;
        cleanupSignal();
        reject(policyError ?? error);
      };
      const abort = () => {
        request.abort();
        failBeforeResponse(new DOMException("Model download aborted", "AbortError"));
      };

      if (init.signal?.aborted) {
        abort();
        return;
      }
      init.signal?.addEventListener("abort", abort, { once: true });

      request.on("redirect", (_statusCode, _method, redirectUrl) => {
        try {
          redirects += 1;
          if (redirects > MAX_REDIRECTS) {
            throw new ModelDownloadError(
              "模型下载跳转次数过多",
              "MODEL_REDIRECT_LIMIT",
            );
          }
          validateModelDownloadUrl(new URL(redirectUrl, initialUrl), allowedHosts);
          // Electron requires this call synchronously inside the redirect event.
          request.followRedirect();
        } catch (error) {
          policyError =
            error instanceof ModelDownloadError
              ? error
              : new ModelDownloadError(
                  "模型下载跳转地址无效",
                  "MODEL_REDIRECT_INVALID",
                );
          request.abort();
        }
      });

      request.on("response", (response) => {
        if (settled) return;
        settled = true;
        const body =
          response.statusCode === 204 || response.statusCode === 304
            ? null
            : (Readable.toWeb(response as unknown as Readable) as ReadableStream);
        const result = new Response(body, {
          status: response.statusCode,
          statusText: response.statusMessage,
          headers: responseHeaders(response.headers),
        });
        const cleanup = () => cleanupSignal();
        response.once("end", cleanup);
        response.once("aborted", cleanup);
        response.once("error", cleanup);
        resolve(result);
      });

      request.once("error", () => failBeforeResponse(networkFailure()));
      request.once("abort", () => {
        failBeforeResponse(
          policyError ??
            (init.signal?.aborted
              ? new DOMException("Model request aborted", "AbortError")
              : networkFailure()),
        );
      });
      request.end();
    });
}
