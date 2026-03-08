# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPEC).resolve().parent
icon_path = project_root / "assets" / "app.ico"


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root), str(project_root / "src")],
    binaries=[],
    datas=[(str(icon_path), "assets")] if icon_path.exists() else [],
    hiddenimports=["tkinterdnd2"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EliteRngLandAuraTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
)

