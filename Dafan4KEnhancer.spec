# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules
from pathlib import Path

project = Path(SPECPATH)
datas = collect_data_files('customtkinter') + collect_data_files('imageio_ffmpeg')
binaries = collect_dynamic_libs('cv2')
hidden = ['cv2.dnn_superres'] + collect_submodules('customtkinter')

# Keep the model cache outside the executable; models are downloaded and verified on demand.
a = Analysis(
    ['app.py'], pathex=[str(project)], binaries=binaries, datas=datas,
    hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'torch', 'tensorflow'], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Dafan4KEnhancer',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False, disable_windowed_traceback=False, argv_emulation=False,
          target_arch=None, codesign_identity=None, entitlements_file=None,
          icon=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[],
               name='Dafan4KEnhancer')
