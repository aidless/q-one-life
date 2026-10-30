# Q-One Desktop Release Runbook

This runbook prepares an internal package. It does not authorize signing,
publishing, tagging a public release, or deploying the website. Those remain
separate account and release gates.

## Artifact Matrix

| Platform | Primary install | Updater payload | Update mode |
| --- | --- | --- | --- |
| Windows 10 22H2/11 x64 | NSIS `.exe` | NSIS `.exe` | Signed automatic update |
| macOS 13+ Apple Silicon | DMG | ZIP | Signed automatic update |
| Ubuntu 22.04+ class Linux x64 | AppImage or deb | AppImage | AppImage automatic; deb manual |

The target declarations do not replace real-machine validation. Put a platform
into public system requirements only after its clean-install records exist.

## Internal Build

```bash
cd desktop
pnpm install --frozen-lockfile
pnpm test
pnpm exec electron-builder --publish never

QONE_PLATFORM=linux \
QONE_ARCH=x64 \
QONE_BUILD_PYTHON=/path/to/build/python \
node scripts/release-evidence.mjs --release-dir release
```

The native CI workflow uploads installers, checksum files, SBOM, dependency
inventory, and release evidence as `unsigned-internal`. It must not publish
these artifacts.

## Signing And Verification

Windows:

1. Sign every executable installer with Authenticode.
2. Run `signtool verify /pa /all` against the final installer.
3. Store the command, timestamp, certificate subject, and result.

macOS:

1. Sign with a Developer ID Application certificate and hardened runtime.
2. Notarize the final DMG and updater ZIP.
3. Run `codesign --verify --deep --strict` and `spctl --assess`.
4. Store the notarization request ID and both command outputs.

Linux:

1. Create the AppImage and deb checksum manifest.
2. Sign the release evidence or AppImage with the selected Sigstore identity.
3. Store `cosign verify` output and the public transparency-log receipt.

Only after the native receipts exist may a release job set
`QONE_SIGNATURE_STATUS=signed` and pass the combined receipt through
`QONE_SIGNATURE_RECEIPT`. The receipt filename, size, and SHA-256 are stored in
release evidence. The value is an assertion backed by native verification, not
a substitute for it.

## Update Manifest

Generate the manifest with a private key that is never committed:

```bash
node scripts/create-update-manifest.mjs \
  --release-dir release \
  --channel stable \
  --platform linux \
  --arch x64 \
  --private-key-file /secure/update-private-key.pem \
  --key-id release-2026 \
  --public-key-output /secure/update-public-keys.json \
  --rollback-file release/Q-One-0.9.1-linux-x86_64.AppImage \
  --output-dir release/updates/stable
```

The public key file must be reviewed, embedded as
`desktop/update-public-keys.json`, and included in the tested installer before
automatic updates can become available.

Verify the signed manifest and every referenced byte:

```bash
node scripts/verify-release.mjs \
  --release-dir release \
  --manifest release/updates/stable/manifest.json \
  --public-keys /secure/update-public-keys.json \
  --from-version 0.9.0 \
  --platform linux \
  --arch x64 \
  --require-rollback
```

The command writes `release/evidence/update-verification-<platform>-<arch>.json`
and `release/updates/<channel>/SHA256SUMS.txt`.

## Public Release Gate

- [ ] Windows, Apple Silicon macOS, and Linux x64 native installers built.
- [ ] Windows Authenticode and macOS Developer ID/notarization receipts saved.
- [ ] Linux Sigstore receipt, SBOM, and SHA-256 manifest saved.
- [ ] Update manifest signed; embedded public key matches the signing key.
- [ ] Rollback artifact signed, uploaded, and verified with `--require-rollback`.
- [ ] Clean install, upgrade, data retention, failed-update recovery, and
      rollback exercised on each target.
- [ ] At least three independent real devices recorded per platform.
- [ ] No open P0/P1 issue, data-loss report, or restore failure.
- [ ] RC and GA hashes match; the previous release remains downloadable.
- [ ] Website and GitHub Releases are reviewed before enabling deployment.

If any platform is unsigned, fails clean-install acceptance, or has an open
P0/P1, `1.0.0` is delayed as a whole.

## Current External Blockers

- Production Windows and Apple signing credentials are not configured.
- `desktop/update-public-keys.json` is intentionally empty, so updates remain
  `UPDATE_NOT_CONFIGURED`.
- Internal CI applies a version-controlled local-provider patch to the reviewed
  `q-one-agent` commit. Public release still requires that patch to become a
  reviewed upstream commit.
- Windows and Apple Silicon clean-machine acceptance has not run.
- GitHub Pages and public Releases have not been authorized or deployed.
