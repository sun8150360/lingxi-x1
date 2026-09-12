# -*- mode: python ; coding: utf-8 -*-
datas = []
hiddenimports = []

a = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "OpenGL", "pyqtgraph.examples", "pyqtgraph.opengl"],
    noarchive=False,
)
# The host toolchain adds Poppler's ICU 78 directory to PATH.  PyInstaller
# mistakes those DLLs for Qt dependencies and places them beside the app,
# where they shadow Windows' own ICU shim and make Qt6Core fail to load.
a.binaries = [
    entry
    for entry in a.binaries
    if entry[0].lower() not in {"icuuc.dll", "icudt78.dll"}
]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lingxi-X1",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Lingxi-X1",
)
