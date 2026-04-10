# launcher.spec — PyInstaller 打包配置
# 仅打包启动器本身（tkinter 纯 UI），不捆绑 OCR/爬虫依赖。
# 子进程通过系统/venv Python 运行，无需捆绑。

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'rapidocr_onnxruntime', 'cv2', 'numpy', 'PIL',
        'requests', 'bs4', 'onnxruntime',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RocoLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    icon='roco_icon.ico',
    console=False,       # 不显示黑色控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
