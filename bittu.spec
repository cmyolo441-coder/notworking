# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for BITTU binary build.

Build command:
    pyinstaller bittu.spec

Output will be in dist/bittu/
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all zedpy submodules
zedpy_imports = collect_submodules('zedpy')

# Collect any data files (configs, etc.)
zedpy_data = collect_data_files('zedpy')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=zedpy_data + [
        ('zedpy/*.py', 'zedpy'),  # Include all .py files
    ],
    hiddenimports=zedpy_imports + [
        'textual',
        'rich',
        'zedpy',
        'zedpy.tui',
        'zedpy.tui.app',
        'zedpy.core',
        'zedpy.core.dream',
        'zedpy.core.effort',
        'zedpy.commands',
        'zedpy.config',
        'zedpy.agent',
        'zedpy.llm',
        'zedpy.tools',
    ],
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
    [],
    exclude_binaries=True,
    name='bittu',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='bittu',
)
