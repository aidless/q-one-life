import assert from "node:assert/strict";
import test from "node:test";
import { buildSupportPackage, redactSupportText } from "../support";

test("support package omits secrets, paths, and personal records", () => {
  const support = buildSupportPackage({
    application: {
      version: "1.0.0",
      packaged: true,
      electron: "45.0.0",
      chrome: "140.0.0",
      node: "24.0.0",
    },
    system: {
      platform: "linux",
      release: "6.8.0",
      arch: "x64",
      locale: "zh-CN",
    },
    runtime: {
      backend: "gnome_libsecret",
      cloud_key: "do-not-export",
      backup_directory: "/home/person/private",
      sidecar: { version: "1.0.0", port: 43123 },
      token: "secret",
    },
    events: [
      {
        at: "2026-10-27T00:00:00.000Z",
        kind: "sidecar",
        message: "Authorization: Bearer top-secret; cloud_key=hidden",
      },
    ],
  });
  const serialized = JSON.stringify(support);
  for (const forbidden of [
    "do-not-export",
    "/home/person/private",
    "top-secret",
    "hidden",
  ]) {
    assert.doesNotMatch(serialized, new RegExp(forbidden.replace(/[/]/g, "\\/")));
  }
  assert.match(serialized, /\[OMITTED\]/);
  assert.match(serialized, /\[REDACTED\]/);
  assert.match(serialized, /43123/);
  assert.equal(
    redactSupportText("X-QOne-Capability: abc123"),
    "X-QOne-Capability=[REDACTED]",
  );
});
