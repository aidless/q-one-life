import { createHash, randomUUID } from "node:crypto";
import { createReadStream, promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);
const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const desktopDirectory = path.resolve(scriptDirectory, "..");
const repositoryDirectory = path.resolve(desktopDirectory, "..");

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function fail(message) {
  console.error(`QONE_RELEASE_EVIDENCE_FAILED ${message}`);
  process.exit(1);
}

async function digest(file, algorithm) {
  const hash = createHash(algorithm);
  for await (const chunk of createReadStream(file)) hash.update(chunk);
  return hash.digest("hex");
}

function artifactKind(name) {
  if (name.endsWith(".AppImage")) return "linux-appimage";
  if (name.endsWith(".deb")) return "linux-deb";
  if (name.endsWith(".exe")) return "windows-nsis";
  if (name.endsWith(".dmg")) return "macos-dmg";
  if (name.endsWith(".zip")) return "macos-updater-zip";
  if (name.endsWith(".blockmap")) return "updater-blockmap";
  return "release-metadata";
}

function purl(name, version, ecosystem) {
  if (ecosystem === "npm" && name.startsWith("@")) {
    const [scope, packageName] = name.slice(1).split("/", 2);
    return `pkg:npm/%40${scope}/${packageName}@${version}`;
  }
  return `pkg:${ecosystem}/${encodeURIComponent(name.toLowerCase())}@${version}`;
}

async function nodeComponents() {
  const options = {
    cwd: desktopDirectory,
    maxBuffer: 32 * 1024 * 1024,
    windowsHide: true,
  };
  // execFile cannot launch pnpm's .cmd shim directly on Windows.
  const { stdout } =
    process.platform === "win32"
      ? await execFileAsync(
          process.env.ComSpec || "cmd.exe",
          ["/d", "/s", "/c", "pnpm licenses list --prod --json --long"],
          options,
        )
      : await execFileAsync(
          "pnpm",
          ["licenses", "list", "--prod", "--json", "--long"],
          options,
        );
  const grouped = JSON.parse(stdout);
  const components = [];
  for (const packages of Object.values(grouped)) {
    for (const entry of packages) {
      for (const version of entry.versions) {
        const component = {
          type: "library",
          name: entry.name,
          version,
          "bom-ref": purl(entry.name, version, "npm"),
          properties: [
            { name: "q-one:ecosystem", value: "npm" },
            { name: "q-one:license-expression", value: entry.license || "unknown" },
          ],
        };
        if (
          typeof entry.license === "string" &&
          /^[A-Za-z0-9.+-]+$/.test(entry.license)
        ) {
          component.licenses = [{ license: { id: entry.license } }];
        }
        if (entry.homepage) {
          component.externalReferences = [
            { type: "website", url: entry.homepage },
          ];
        }
        components.push(component);
      }
    }
  }
  return components;
}

function metadataValue(text, key) {
  const match = new RegExp(`^${key}:\\s*(.+)$`, "im").exec(text);
  return match?.[1].trim();
}

async function pythonComponents(releaseDirectory) {
  const candidates = [
    path.join(
      releaseDirectory,
      "linux-unpacked",
      "resources",
      "sidecar",
      "_internal",
    ),
    path.join(
      releaseDirectory,
      "win-unpacked",
      "resources",
      "sidecar",
      "_internal",
    ),
    path.join(
      releaseDirectory,
      "mac-arm64",
      "Q-One.app",
      "Contents",
      "Resources",
      "sidecar",
      "_internal",
    ),
    path.join(
      releaseDirectory,
      "mac",
      "Q-One.app",
      "Contents",
      "Resources",
      "sidecar",
      "_internal",
    ),
  ];
  let metadataDirectory;
  for (const candidate of candidates) {
    if (await fs.stat(candidate).then((value) => value.isDirectory()).catch(() => false)) {
      metadataDirectory = candidate;
      break;
    }
  }
  if (!metadataDirectory) return [];

  const metadataDirectories = [];
  async function walk(directory) {
    const entries = await fs.readdir(directory, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (entry.name.endsWith(".dist-info")) {
        metadataDirectories.push(path.join(directory, entry.name));
      } else {
        await walk(path.join(directory, entry.name));
      }
    }
  }
  await walk(metadataDirectory);

  const byPackage = new Map();
  for (const metadataDirectoryPath of metadataDirectories) {
    const metadataPath = path.join(metadataDirectoryPath, "METADATA");
    const text = await fs.readFile(metadataPath, "utf8").catch(() => "");
    const name = metadataValue(text, "Name");
    const version = metadataValue(text, "Version");
    if (!name || !version) continue;
    const key = `${name.toLowerCase()}@${version}`;
    if (byPackage.has(key)) continue;
    const license = metadataValue(text, "License-Expression") || metadataValue(text, "License");
    const component = {
      type: "library",
      name,
      version,
      "bom-ref": purl(name, version, "pypi"),
      properties: [
        { name: "q-one:ecosystem", value: "python" },
        { name: "q-one:license-expression", value: license || "unknown" },
        { name: "q-one:distribution", value: "bundled-sidecar-metadata" },
      ],
    };
    if (license && /^[A-Za-z0-9.+-]+$/.test(license)) {
      component.licenses = [{ license: { id: license } }];
    }
    byPackage.set(key, component);
  }
  return [...byPackage.values()];
}

async function pythonBuildInventory() {
  const python = process.env.QONE_BUILD_PYTHON;
  if (!python) {
    return {
      available: false,
      reason: "QONE_BUILD_PYTHON is not set",
      count: 0,
      components: [],
    };
  }
  try {
    const { stdout } = await execFileAsync(python, ["-m", "pip", "inspect", "--local"], {
      maxBuffer: 64 * 1024 * 1024,
      windowsHide: true,
    });
    const inspected = JSON.parse(stdout);
    const components = (inspected.installed || [])
      .map((item) => {
        const metadata = item.metadata || {};
        return {
          name: metadata.name,
          version: metadata.version,
          requested: Boolean(item.requested),
        };
      })
      .filter((item) => typeof item.name === "string" && typeof item.version === "string")
      .sort((left, right) =>
        `${left.name}@${left.version}`.localeCompare(`${right.name}@${right.version}`),
      );
    return { available: true, count: components.length, components };
  } catch (error) {
    return {
      available: false,
      reason: error instanceof Error ? error.message : String(error),
      count: 0,
      components: [],
    };
  }
}

function enforceLicensePolicy(components) {
  const denied = /\b(?:AGPL|GPL|SSPL|BUSL|Commons-Clause)\b/i;
  const violations = components
    .map((component) => ({
      name: component.name,
      version: component.version,
      license:
        component.properties?.find(
          (property) => property.name === "q-one:license-expression",
        )?.value ?? "unknown",
    }))
    .filter((component) => denied.test(component.license));
  if (violations.length) {
    throw new Error(
      `license policy rejected: ${violations
        .map((item) => `${item.name}@${item.version} ${item.license}`)
        .join(", ")}`,
    );
  }
}

async function main() {
  const releaseDirectory = path.resolve(
    argument("--release-dir", path.join(desktopDirectory, "release")),
  );
  const outputDirectory = path.resolve(
    argument("--output", path.join(releaseDirectory, "evidence")),
  );
  const signatureStatus = process.env.QONE_SIGNATURE_STATUS ?? "unsigned-internal";
  const notarizationStatus =
    process.env.QONE_NOTARIZATION_STATUS ?? "not-applicable";
  const signatureReceiptPath = process.env.QONE_SIGNATURE_RECEIPT;
  let signatureReceipt;
  if (signatureStatus === "signed") {
    if (!signatureReceiptPath) {
      fail("signed status requires QONE_SIGNATURE_RECEIPT");
    }
    const resolvedReceipt = path.resolve(signatureReceiptPath);
    const receiptStat = await fs.stat(resolvedReceipt).catch(() => null);
    if (!receiptStat?.isFile() || receiptStat.size === 0) {
      fail("signature receipt is missing or empty");
    }
    signatureReceipt = {
      name: path.basename(resolvedReceipt),
      bytes: receiptStat.size,
      sha256: await digest(resolvedReceipt, "sha256"),
    };
  }
  if (hasFlag("--require-signed") && signatureStatus !== "signed") {
    fail("signature status must be signed for a public release");
  }

  const packageJson = JSON.parse(
    await fs.readFile(path.join(desktopDirectory, "package.json"), "utf8"),
  );
  const baseline = JSON.parse(
    await fs.readFile(path.join(desktopDirectory, "baseline.json"), "utf8"),
  );
  const candidateNames = await fs.readdir(releaseDirectory);
  const artifactNames = candidateNames
    .filter((name) =>
      /\.(?:AppImage|deb|exe|dmg|zip|blockmap)$/i.test(name),
    )
    .sort();
  if (!artifactNames.length) fail(`no packages found in ${releaseDirectory}`);

  const artifacts = [];
  for (const name of artifactNames) {
    const file = path.join(releaseDirectory, name);
    const stat = await fs.stat(file);
    if (!stat.isFile()) continue;
    artifacts.push({
      name,
      kind: artifactKind(name),
      bytes: stat.size,
      sha256: await digest(file, "sha256"),
      sha512: await digest(file, "sha512"),
    });
  }

  const node = await nodeComponents();
  const python = await pythonComponents(releaseDirectory);
  const pythonBuild = await pythonBuildInventory();
  const components = [
    ...node,
    ...python,
    {
      type: "data",
      name: "Qwen3-0.6B-Q8_0.gguf",
      version: "23749fefcc72300e3a2ad315e1317431b06b590a",
      "bom-ref":
        "pkg:generic/qwen3-0.6b-q8_0@23749fefcc72300e3a2ad315e1317431b06b590a",
      licenses: [{ license: { id: "Apache-2.0" } }],
      properties: [
        {
          name: "q-one:distribution",
          value: "optional-download-not-bundled",
        },
        {
          name: "q-one:sha256",
          value:
            "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031",
        },
      ],
    },
  ];
  enforceLicensePolicy(node.concat(python));

  const sbom = {
    bomFormat: "CycloneDX",
    specVersion: "1.5",
    serialNumber: `urn:uuid:${randomUUID()}`,
    version: 1,
    metadata: {
      timestamp: new Date().toISOString(),
      tools: [
        {
          vendor: "Q-One",
          name: "release-evidence",
          version: "1",
        },
      ],
      component: {
        type: "application",
        name: "q-one",
        version: packageJson.version,
        licenses: [{ license: { id: "MIT" } }],
      },
      properties: [
        { name: "q-one:platform", value: process.env.QONE_PLATFORM ?? os.platform() },
        { name: "q-one:arch", value: process.env.QONE_ARCH ?? os.arch() },
        {
          name: "q-one:source-commit",
          value: process.env.GITHUB_SHA ?? "workspace",
        },
      ],
    },
    components,
  };

  const evidence = {
    schema: "q-one-release-evidence-v1",
    generated_at: new Date().toISOString(),
    application: {
      name: "Q-One",
      version: packageJson.version,
      license: "MIT",
      source_commit: process.env.GITHUB_SHA ?? null,
    },
    platform: process.env.QONE_PLATFORM ?? os.platform(),
    arch: process.env.QONE_ARCH ?? os.arch(),
    signature: {
      status: signatureStatus,
      notarization: notarizationStatus,
      receipt: signatureReceipt ?? null,
      public_release_eligible: signatureStatus === "signed",
    },
    baseline,
    artifacts,
    dependency_counts: {
      npm: node.length,
      python_bundled: python.length,
      python_build_environment: pythonBuild.count,
    },
    build_environment: {
      python: pythonBuild,
    },
  };

  await fs.mkdir(outputDirectory, { recursive: true, mode: 0o755 });
  await fs.writeFile(
    path.join(outputDirectory, "SHA256SUMS.txt"),
    `${artifacts.map((item) => `${item.sha256}  ${item.name}`).join("\n")}\n`,
  );
  await fs.writeFile(
    path.join(outputDirectory, "release-evidence.json"),
    `${JSON.stringify(evidence, null, 2)}\n`,
  );
  await fs.writeFile(
    path.join(outputDirectory, "sbom.cdx.json"),
    `${JSON.stringify(sbom, null, 2)}\n`,
  );
  await fs.writeFile(
    path.join(outputDirectory, "licenses.json"),
    `${JSON.stringify(
      components.map((component) => ({
        ecosystem:
          component.properties?.find(
            (property) => property.name === "q-one:ecosystem",
          )?.value ?? "other",
        name: component.name,
        version: component.version,
        license:
          component.properties?.find(
            (property) =>
              property.name === "q-one:license-expression",
          )?.value ?? "Apache-2.0",
      })),
      null,
      2,
    )}\n`,
  );
  await fs.writeFile(
    path.join(outputDirectory, "python-build-inventory.json"),
    `${JSON.stringify(pythonBuild, null, 2)}\n`,
  );
  console.log(
    `QONE_RELEASE_EVIDENCE_OK ${JSON.stringify({
      artifacts: artifacts.length,
      components: components.length,
      output: outputDirectory,
      signature: signatureStatus,
    })}`,
  );
}

main().catch((error) => {
  fail(error instanceof Error ? error.message : String(error));
});
