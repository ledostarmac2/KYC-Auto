# -*- mode: python ; coding: utf-8 -*-

import os


datas = [
    ('../KYCReminder.exe', 'payload'),
    ('msedgedriver.exe', 'payload'),
]
icon_path = None

if os.path.exists('assets/KYCReminder.ico'):
    datas.append(('assets/KYCReminder.ico', 'assets'))
    icon_path = 'assets/KYCReminder.ico'

if os.path.exists('Driver_Notes/LICENSE'):
    datas.append(('Driver_Notes/LICENSE', 'licenses'))

if os.path.exists('Driver_Notes/EULA'):
    datas.append(('Driver_Notes/EULA', 'licenses'))


a = Analysis(
    ['setup_wizard.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='KYCReminderSetup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
