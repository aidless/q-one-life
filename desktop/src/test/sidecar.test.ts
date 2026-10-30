import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  defaultSidecarLaunch,
  sanitizeSidecarLog,
  SidecarProcess,
} from "../sidecar";
import {
  directoryIsEmpty,
  legacyDataPath,
  migrateLegacyData,
} from "../migration";

test("default sidecar launch is argument-safe", () => {
  const launch = defaultSidecarLaunch("/tmp/data with spaces", {
    QONE_PYTHON: "/tmp/python",
  });
  assert.equal(launch.executable, "/tmp/python");
  assert.deepEqual(launch.args, [
    "-m",
    "qone_life.sidecar",
    "--data-dir",
    "/tmp/data with spaces",
  ]);
});

test("sidecar diagnostics redact handshake and authorization secrets", () => {
  const redacted = sanitizeSidecarLog(
    'request X-QOne-Capability: capability-secret Bearer bearer-secret ' +
      '{"cloud_key":"cloud-secret","local_model_token":"model-secret"}',
  );
  assert.doesNotMatch(redacted, /capability-secret|bearer-secret|cloud-secret|model-secret/);
  assert.match(redacted, /\[REDACTED\]/);
});

test("missing sidecar executable fails without an unhandled stdin error", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-missing-sidecar-"));
  const sidecar = new SidecarProcess(
    { executable: path.join(folder, "missing-sidecar"), args: [] },
    2_000,
  );
  await assert.rejects(sidecar.start());
  await fs.rm(folder, { recursive: true, force: true });
});

test("legacy data migration copies and verifies a tree", async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "qone-migration-"));
  const source = path.join(root, "source");
  const target = path.join(root, "target");
  await fs.mkdir(path.join(source, "nested"), { recursive: true });
  await fs.writeFile(path.join(source, "settings.json"), '{"language":"zh-CN"}');
  await fs.writeFile(path.join(source, "nested", "records.jsonl"), "one\ntwo\n");
  const result = await migrateLegacyData(source, target, { checkLegacyServer: false });
  assert.equal(result.status, "migrated");
  assert.equal(await directoryIsEmpty(target), false);
  assert.equal(await fs.readFile(path.join(target, "settings.json"), "utf8"), '{"language":"zh-CN"}');
  const manifest = JSON.parse(
    await fs.readFile(path.join(target, ".q-one-migration.json"), "utf8"),
  );
  assert.equal(manifest.version, 1);
  assert.equal(manifest.files.length, 2);
  assert.equal(await fs.readFile(path.join(target, "nested", "records.jsonl"), "utf8"), "one\ntwo\n");
});

test("legacy path remains the documented Linux-compatible location", () => {
  assert.equal(
    legacyDataPath("/home/example"),
    path.join("/home/example", ".local", "share", "q-one"),
  );
});

test("desktop sidecar handshake carries only the local model session fields it needs", async () => {
  const { sidecarHandshake } = await import("../sidecar.js");
  const handshake = sidecarHandshake(
    "c".repeat(43),
    "k".repeat(43),
    undefined,
    "zh-CN",
    {
      url: "http://127.0.0.1:41234/v1",
      name: "Qwen3-0.6B-Q8_0",
      token: "m".repeat(43),
    },
  );
  assert.equal(handshake.local_model_url, "http://127.0.0.1:41234/v1");
  assert.equal(handshake.local_model_name, "Qwen3-0.6B-Q8_0");
  assert.equal(handshake.local_model_token, "m".repeat(43));
  assert.equal(handshake.locale, "zh-CN");
  assert.equal("cloud_key" in handshake, false);
});
