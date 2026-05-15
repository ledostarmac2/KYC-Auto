# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules
import os

selenium_hiddenimports = (
    collect_submodules('selenium.webdriver.edge')
    + collect_submodules('selenium.webdriver.chromium')
)

datas = []
icon_path = None
if os.path.exists('assets/KYCReminder.ico'):
    datas.append(('assets/KYCReminder.ico', 'assets'))
    icon_path = 'assets/KYCReminder.ico'


a = Analysis(
    ['kyc_reminder.py'],
    pathex=[],
    binaries=[('msedgedriver.exe', '.')],
    datas=datas,
    hiddenimports=['kyc_automation'] + selenium_hiddenimports,
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
    name='KYCReminder',
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
