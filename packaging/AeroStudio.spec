# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPEC).resolve().parents[1]
codrone_datas, codrone_binaries, codrone_hiddenimports = collect_all("codrone_edu")
app_icon = (
    ROOT / "packaging" / "codrone_studio.icns"
    if sys.platform == "darwin"
    else ROOT / "packaging" / "codrone_studio.ico"
)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=codrone_binaries,
    datas=[(str(ROOT / "assets"), "assets"), *codrone_datas],
    hiddenimports=codrone_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AeroStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(app_icon),
)

collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="AeroStudio",
)

if sys.platform == "darwin":
    app = BUNDLE(
        collection,
        name="AeroStudio.app",
        icon=str(app_icon),
        bundle_identifier="org.muslimsintech.aerostudio",
        version="1.0.0",
        info_plist={
            "CFBundleDisplayName": "AeroStudio",
            "NSHighResolutionCapable": True,
        },
    )
