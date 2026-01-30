# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_metadata

a = Analysis(
    ['src/order_management/app.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src/order_management/assets', 'order_management/assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
a.datas += collect_metadata('bp-order-management')

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BP-Order-Management',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/order_management/assets/bp-logo.ico',
)
