# -*- mode: python ; coding: utf-8 -*-
# Tumeloroot PyInstaller Spec

import os
import sys

block_cipher = None

# Paths
ROOT = os.path.dirname(os.path.abspath(SPEC))
TUMELOROOT = os.path.join(ROOT, 'tumeloroot')

a = Analysis(
    [os.path.join(TUMELOROOT, '__main__.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(TUMELOROOT, 'devices', '*.yaml'), 'tumeloroot/devices'),
        (os.path.join(TUMELOROOT, 'gui', 'resources', 'styles', '*.qss'), 'tumeloroot/gui/resources/styles'),
    ],
    hiddenimports=[
        'tumeloroot',
        'tumeloroot.core',
        'tumeloroot.core.engine',
        'tumeloroot.core.device_profile',
        'tumeloroot.core.mtk_bridge',
        'tumeloroot.core.adb_bridge',
        'tumeloroot.core.magisk_patcher',
        'tumeloroot.core.vbmeta_patcher',
        'tumeloroot.core.backup_manager',
        'tumeloroot.core.prerequisite_checker',
        'tumeloroot.core.platform_utils',
        'tumeloroot.gui',
        'tumeloroot.gui.wizard',
        'tumeloroot.gui.theme',
        'tumeloroot.gui.pages.welcome_page',
        'tumeloroot.gui.pages.prerequisites_page',
        'tumeloroot.gui.pages.connect_page',
        'tumeloroot.gui.pages.backup_page',
        'tumeloroot.gui.pages.unlock_page',
        'tumeloroot.gui.pages.patch_page',
        'tumeloroot.gui.pages.verify_page',
        'tumeloroot.gui.pages.complete_page',
        'tumeloroot.gui.widgets.log_console',
        'tumeloroot.gui.widgets.progress_panel',
        'tumeloroot.gui.widgets.device_info_card',
        'tumeloroot.gui.widgets.device_animation',
        'yaml',
        'usb',
        'usb.core',
        'usb.backend',
        'usb.backend.libusb1',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL'],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Tumeloroot',
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
    name='Tumeloroot',
)
