import assert from "node:assert/strict";
import test from "node:test";
import { proxyRulesFromEnvironment } from "../model-network";

test("model network uses standard proxy environment without changing hosts", () => {
  assert.equal(
    proxyRulesFromEnvironment({ HTTPS_PROXY: "http://127.0.0.1:7897" }),
    "http://127.0.0.1:7897/",
  );
  assert.equal(
    proxyRulesFromEnvironment({ https_proxy: "socks5://127.0.0.1:1080" }),
    "socks5://127.0.0.1:1080",
  );
  assert.equal(proxyRulesFromEnvironment({ NO_PROXY: "example.com" }), undefined);
  assert.equal(
    proxyRulesFromEnvironment({ HTTPS_PROXY: "https://proxy.example/path" }),
    undefined,
  );
});
