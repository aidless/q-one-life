import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("qoneDesktop", {
  runtimeInfo: () => ipcRenderer.invoke("qone:runtime-info"),
  secretStatus: () => ipcRenderer.invoke("qone:secret-status"),
  setCloudKey: (value: string) => ipcRenderer.invoke("qone:set-cloud-key", value),
  clearCloudKey: () => ipcRenderer.invoke("qone:clear-cloud-key"),
  backupStatus: () => ipcRenderer.invoke("qone:backup-status"),
  chooseBackupDirectory: () => ipcRenderer.invoke("qone:backup-choose-directory"),
  setBackupEnabled: (enabled: boolean) => ipcRenderer.invoke("qone:backup-set-enabled", enabled),
  enableAutoBackup: (confirmed: boolean) =>
    ipcRenderer.invoke("qone:backup-enable-auto", confirmed),
  backupNow: () => ipcRenderer.invoke("qone:backup-now"),
  inspectBackup: () => ipcRenderer.invoke("qone:backup-inspect"),
  restoreBackup: (recoveryKeyText: string) =>
    ipcRenderer.invoke("qone:backup-restore", recoveryKeyText),
  modelStatus: () => ipcRenderer.invoke("qone:model-status"),
  downloadModel: () => ipcRenderer.invoke("qone:model-download"),
  cancelModelDownload: () => ipcRenderer.invoke("qone:model-cancel"),
  removeModel: () => ipcRenderer.invoke("qone:model-remove"),
  previewSupportPackage: () => ipcRenderer.invoke("qone:support-preview"),
  exportSupportPackage: () => ipcRenderer.invoke("qone:support-export"),
  onModelStatus: (callback: (status: unknown) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, status: unknown) => callback(status);
    ipcRenderer.on("qone:model-status", listener);
    return () => ipcRenderer.removeListener("qone:model-status", listener);
  },
  updateStatus: () => ipcRenderer.invoke("qone:update-status"),
  checkForUpdates: () => ipcRenderer.invoke("qone:update-check"),
  downloadUpdate: () => ipcRenderer.invoke("qone:update-download"),
  installUpdate: () => ipcRenderer.invoke("qone:update-install"),
  openUpdateDownload: (kind: "update" | "rollback") =>
    ipcRenderer.invoke("qone:update-open-download", kind),
  onUpdateStatus: (callback: (status: unknown) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, status: unknown) => callback(status);
    ipcRenderer.on("qone:update-status", listener);
    return () => ipcRenderer.removeListener("qone:update-status", listener);
  },
});
