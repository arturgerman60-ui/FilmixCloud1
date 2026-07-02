# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for FunPay AutoResponder.

Build with:  pyinstaller FunPayAutoResponder.spec
Produces a one-folder (onedir) distribution in dist/FunPayAutoResponder.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

BASE = Path(SPECPATH)

datas = [
    (str(BASE / "src" / "assets"), "assets"),
    (str(BASE / "plugins"), "plugins"),
]

hiddenimports = []
hiddenimports += collect_submodules("customtkinter")
hiddenimports += collect_submodules("apscheduler")
hiddenimports += ["keyring.backends", "pystray._win32", "PIL._tkinter_finder"]

block_cipher = None

a = Analysis(
    ["src/main.py"],
    pathex=[str(BASE)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["playwright"] if "--no-playwright" in sys.argv else [],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FunPayAutoResponder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # windowed app (no console)
    icon=str(BASE / "src" / "assets" / "icons" / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FunPayAutoResponder",
)
