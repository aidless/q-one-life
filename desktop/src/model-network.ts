export type NetworkEnvironment = Record<string, string | undefined>;

const SUPPORTED_PROXY_PROTOCOLS = new Set([
  "http:",
  "https:",
  "socks4:",
  "socks5:",
]);

export function proxyRulesFromEnvironment(
  env: NetworkEnvironment,
): string | undefined {
  const candidate =
    env.HTTPS_PROXY ||
    env.https_proxy ||
    env.ALL_PROXY ||
    env.all_proxy ||
    env.HTTP_PROXY ||
    env.http_proxy;
  if (!candidate) return undefined;
  try {
    const url = new URL(candidate);
    if (
      !SUPPORTED_PROXY_PROTOCOLS.has(url.protocol) ||
      !url.hostname ||
      (url.pathname !== "/" && url.pathname !== "") ||
      url.search ||
      url.hash
    ) {
      return undefined;
    }
    return url.href;
  } catch {
    return undefined;
  }
}
