const { promises: fs } = require("node:fs");
const path = require("node:path");

const allowedBackends = {
  linux: ["linux-x64", "linux-x64-vulkan"],
  darwin: ["mac-arm64-metal"],
  win32: ["win-x64", "win-x64-vulkan"],
};

exports.default = async function afterPack(context) {
  const allowed = allowedBackends[context.electronPlatformName];
  if (!allowed) {
    throw new Error(`unsupported package platform: ${context.electronPlatformName}`);
  }

  const backendRoot = path.join(
    context.packager.getResourcesDir(context.appOutDir),
    "app.asar.unpacked",
    "node_modules",
    "@node-llama-cpp",
  );
  let entries;
  try {
    entries = await fs.readdir(backendRoot, { withFileTypes: true });
  } catch (error) {
    throw new Error(`node-llama-cpp backends are missing: ${String(error)}`);
  }

  const available = new Set(
    entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name),
  );
  for (const backend of allowed) {
    if (!available.has(backend)) {
      throw new Error(
        `required node-llama-cpp backend ${backend} is missing for ${context.electronPlatformName}`,
      );
    }
  }

  for (const entry of entries) {
    if (!entry.isDirectory() || allowed.includes(entry.name)) continue;
    await fs.rm(path.join(backendRoot, entry.name), { recursive: true, force: true });
  }

  console.log(
    `[q-one] retained node-llama-cpp backends: ${allowed.join(", ")}`,
  );
};
