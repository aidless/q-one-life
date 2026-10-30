# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from importlib.metadata import distributions

repo = Path(SPECPATH).resolve().parent
workspace = repo.parent
pathex = []
for sibling in ("q-one-life", "q-one-core", "q-one-agent"):
    source = workspace / sibling / "src"
    if source.is_dir():
        pathex.append(str(source))

hiddenimports = (
    collect_submodules("qone_life")
    + collect_submodules("qone_core")
    + collect_submodules("qone_agent")
    + ["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
       "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
       "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"]
)

python_metadata_datas = []
seen_metadata = set()
build_only = {
    "altgraph",
    "packaging",
    "pip",
    "pyinstaller",
    "pyinstaller-hooks-contrib",
    "setuptools",
}
for distribution in distributions():
    package_name = (distribution.metadata.get("Name") or "").lower()
    if package_name in build_only:
        continue
    distribution_path = getattr(distribution, "_path", None)
    if distribution_path is None:
        continue
    metadata = Path(distribution_path) / "METADATA"
    if not metadata.is_file():
        continue
    # Keep only package metadata, not local installer records or absolute paths.
    package_key = (distribution.metadata.get("Name") or "", distribution.version or "")
    if package_key in seen_metadata:
        continue
    seen_metadata.add(package_key)
    python_metadata_datas.append(
        (str(metadata), f"python-dist-info/{metadata.parent.name}")
    )

a = Analysis(
    ["sidecar_entry.py"],
    pathex=pathex,
    binaries=[],
    datas=(
        collect_data_files("qone_life", includes=["static/*"])
        + python_metadata_datas
    ),
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["laya", "torch", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="qone-life-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="qone-life-sidecar",
)
