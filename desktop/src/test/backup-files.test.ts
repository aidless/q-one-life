import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  effectiveAutomaticBackup,
  pruneAutomaticBackups,
} from "../backup-files";

test("automatic backup is paused when secrets cannot persist", () => {
  assert.deepEqual(effectiveAutomaticBackup(true, false, true), {
    enabled: false,
    paused: true,
    pauseReason: "SECRET_STORE_SESSION_ONLY",
  });
  assert.deepEqual(effectiveAutomaticBackup(true, true, false), {
    enabled: false,
    paused: true,
    pauseReason: "RECOVERY_KEY_MISSING",
  });
  assert.deepEqual(effectiveAutomaticBackup(true, true, true), {
    enabled: true,
    paused: false,
    pauseReason: null,
  });
  assert.deepEqual(effectiveAutomaticBackup(false, false, false), {
    enabled: false,
    paused: false,
    pauseReason: null,
  });
});

test("automatic backup rotation keeps the newest files and manual backups", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "qone-backups-"));
  const names = Array.from(
    { length: 9 },
    (_, index) => `Q-One-autosave-2026-10-${String(index + 1).padStart(2, "0")}.qonebackup`,
  );
  for (const [index, name] of names.entries()) {
    const file = path.join(folder, name);
    await fs.writeFile(file, name);
    const timestamp = new Date(2026, 9, index + 1);
    await fs.utimes(file, timestamp, timestamp);
  }
  await fs.writeFile(path.join(folder, "Q-One-backup-manual.qonebackup"), "manual");
  await fs.writeFile(path.join(folder, "notes.txt"), "unrelated");

  await pruneAutomaticBackups(folder, 7);

  const remaining = (await fs.readdir(folder)).sort();
  assert.deepEqual(remaining, [
    "Q-One-autosave-2026-10-03.qonebackup",
    "Q-One-autosave-2026-10-04.qonebackup",
    "Q-One-autosave-2026-10-05.qonebackup",
    "Q-One-autosave-2026-10-06.qonebackup",
    "Q-One-autosave-2026-10-07.qonebackup",
    "Q-One-autosave-2026-10-08.qonebackup",
    "Q-One-autosave-2026-10-09.qonebackup",
    "Q-One-backup-manual.qonebackup",
    "notes.txt",
  ]);
});
