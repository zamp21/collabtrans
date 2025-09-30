# -*- mode: python ; coding: utf-8 -*-
# 最小化Lite版本配置 - 只包含核心功能
import os
import sys
from PyInstaller.utils.hooks import collect_data_files
import collabtrans

# 最小化数据文件
datas = [
    ('collabtrans/static', 'collabtrans/static'),
    ('collabtrans/template', 'collabtrans/template'),
    # 排除pygments的大数据文件
]

# 最小化隐藏导入
hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    # 不包含pygments，减少大小
]

a = Analysis(
    ['collabtrans/app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 所有大依赖包
        "docling", "collabtrans.converter.x2md.converter_docling",
        "collabtrans.converter.x2md.converter_mineru",
        "torch", "torchvision", "torchaudio",
        "transformers", "tokenizers", "sentencepiece",
        "easyocr", "cv2", "opencv-python",
        "scipy", "pandas", "matplotlib", "seaborn",
        "sklearn", "scikit-learn",
        "nltk", "spacy", "gensim", "jieba",
        "celery", "sqlalchemy",
        "pytest", "pytest-asyncio", "pytest-cov",
        "black", "flake8", "mypy",
        "jupyter", "ipython", "notebook",
        "tensorflow", "keras",
        "xgboost", "lightgbm",
        # 排除pygments以减少大小
        "pygments",
        # 排除一些可选功能
        "collabtrans.converter.x2xlsx",
        "collabtrans.exporter.epub",
        "collabtrans.exporter.srt",
        # 排除一些大的工具模块
        "collabtrans.utils.redis_manager",  # 如果不需要Redis功能
    ],
    noarchive=False,
    optimize=2,  # 启用Python字节码优化
)

pyz = PYZ(a.pure)

platform_suffix = 'win' if sys.platform.startswith('win') else ('mac' if sys.platform == 'darwin' else 'linux')

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'CollabTrans-minimal-{collabtrans.__version__}-{platform_suffix}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 启用符号剥离
    upx=True,    # 启用UPX压缩
    upx_exclude=[],  # 可以排除某些文件不被UPX压缩
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='CollabTrans.ico',
)
