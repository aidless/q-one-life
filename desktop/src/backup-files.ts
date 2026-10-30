import { promises as fs } from "node:fs";
import path from "node:path";

export const AUTO_BACKUP_RETENTION = 7;

export type BackupPauseReason =
  | "SECRET_STORE_SESSION_ONLY"
  | "RECOVERY_KEY_MISSING";

export interface EffectiveBackupState {
  enabled: boolean;
  paused: boolean;
  pauseReason: BackupPauseReason | null;
}

export function effectiveAutomaticBackup(
  configuredEnabled: boolean,
  secretPersistent: boolean,
  recoveryKeyAvailable: boolean,
): EffectiveBackupState {
  if (!configuredEnabled) {
    return { enabled: false, paused: false, pauseReason: null };
  }
  if (!secretPersistent) {
    return {
      enabled: false,
      paused: true,
      pauseReason: "SECRET_STORE_SESSION_ONLY",
    };
  }
  if (!recoveryKeyAvailable) {
    return {
      enabled: false,
      paused: true,
      pauseReason: "RECOVERY_KEY_MISSING",
    };
  }
  return { enabled: true, paused: false, pauseReason: null };
}

export async function pruneAutomaticBackups(
  directory: string,
  retention = AUTO_BACKUP_RETENTION,
): Promise<void> {
  if (!Number.isInteger(retention) || retention < 1) {
    throw new Error("backup retention must be a positive integer");
  }
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const automatic = await Promise.all(
    entries
      .filter(
        (entry) =>
          entry.isFile() &&
          /^Q-One-autosave-\d{4}-\d{2}-\d{2}\.qonebackup$/.test(entry.name),
      )
      .map(async (entry) => {
        const file = path.join(directory, entry.name);
        return { file, stat: await fs.stat(file) };
      }),
  );
  automatic.sort((left, right) => right.stat.mtimeMs - left.stat.mtimeMs);
  await Promise.all(
    automatic.slice(retention).map(({ file }) => fs.rm(file, { force: true })),
  );
}
