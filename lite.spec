# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files
import collabtrans

datas = [
    ('collabtrans/static', 'collabtrans/static'),
    ('collabtrans/template', 'collabtrans/template'),
    ('collabtrans/i18n', 'collabtrans/i18n'),  # 添加i18n目录
    ('collabtrans/static/favicon.ico', 'collabtrans/favicon.ico'),
    ('global_config.json', '.'),  # 全局配置文件
    ('app_config.json', '.'),  # 应用配置文件（默认，运行时优先 /etc）
    ('local_secrets.json.template', '.'),  # 本地密钥模板文件
    ('setup_secrets.py', '.'),  # 敏感配置初始化脚本
    ('setup_first_deploy.py', '.'),  # 首次部署设置脚本
    # 只包含必要的pygments数据，排除大文件
    *collect_data_files('pygments', include_py_files=False)  # 只包含数据文件，不包含Python文件
]

hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments'
]

a = Analysis(
    ['collabtrans/app.py'],  # 使用正斜杠，Windows 也支持
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-numpy-fix.py'],
    excludes=[
        # 大依赖包
        "docling", "collabtrans.converter.x2md.converter_docling",
        "torch", "torchvision", "torchaudio",
        "transformers", "tokenizers", "sentencepiece",
        "easyocr", "cv2", "opencv-python",
        "scipy", "pandas", "matplotlib", "seaborn",
        "sklearn", "scikit-learn",
        "nltk", "spacy", "gensim", "jieba",
        "celery", "sqlalchemy",
        # 可选功能模块
        "collabtrans.converter.x2md.converter_docling",
        # 测试和开发工具
        "pytest", "pytest-asyncio", "pytest-cov",
        "black", "flake8", "mypy",
        # 其他大包
        "jupyter", "ipython", "notebook",
        "tensorflow", "keras",
        "xgboost", "lightgbm",
        # numpy相关（如果导致兼容性问题）
        "numpy",
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
    name=f'CollabTrans-{collabtrans.__version__}-{platform_suffix}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='CollabTrans.ico',  # 修正为字符串
)