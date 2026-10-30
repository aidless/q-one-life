import { fetch as undiciFetch, ProxyAgent } from "undici";
import { ModelFetch } from "./model-files";

export interface ProxyModelFetch {
  fetchImpl: ModelFetch;
  close: () => Promise<void>;
}

/**
 * Managed Linux desktops often expose a proxy only through environment
 * variables. Electron's Chromium stack is preferred, but Node's TLS path with
 * an explicit CONNECT proxy is the deterministic fallback for that setup.
 */
export function createProxyModelFetch(proxyUrl: string): ProxyModelFetch {
  const dispatcher = new ProxyAgent(proxyUrl);
  return {
    fetchImpl: async (input, init = {}) =>
      (await undiciFetch(
        input as string | URL,
        { ...init, dispatcher } as unknown as Parameters<typeof undiciFetch>[1],
      )) as unknown as Response,
    close: () => dispatcher.close(),
  };
}
