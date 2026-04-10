# launcher.spec — PyInstaller 打包配置
# 全功能打包：所有工具模块、OCR 模型、依赖库均打入单一 exe。
# 发行时将 exe 与 data/ 文件夹一起打包为 zip 分发。

block_cipher = None

_rapidocr = '.venv/Lib/site-packages/rapidocr_onnxruntime'

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        # rapidocr 模型及配置（非 Python 文件需手动列出）
        (f'{_rapidocr}/config.yaml',                  'rapidocr_onnxruntime'),
        (f'{_rapidocr}/ch_ppocr_v2_cls',              'rapidocr_onnxruntime/ch_ppocr_v2_cls'),
        (f'{_rapidocr}/ch_ppocr_v3_det',              'rapidocr_onnxruntime/ch_ppocr_v3_det'),
        (f'{_rapidocr}/ch_ppocr_v3_rec',              'rapidocr_onnxruntime/ch_ppocr_v3_rec'),
        (f'{_rapidocr}/models',                       'rapidocr_onnxruntime/models'),
    ],
    hiddenimports=[
        'damage_gui',
        'roco.analyzer',
        'roco.calculator',
        'roco.scraper.spirits',
        'roco.scraper.skills',
        'roco.data',
        'roco.stats',
        'roco.constants',
        'rapidocr_onnxruntime',
        'onnxruntime',
        'onnxruntime.capi._pybind_state',
        'cv2',
        'numpy',
        'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw', 'PIL.ImageFont',
        'requests',
        'bs4',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
