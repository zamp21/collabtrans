# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files
import collabtrans

datas = [
    ('collabtrans/static', 'collabtrans/static'),
    ('collabtrans/template', 'collabtrans/template'),
    ('collabtrans/i18n', 'collabtrans/i18n'),  # Add i18n directory
    ('collabtrans/static/favicon.ico', 'collabtrans/favicon.ico'),
    ('global_config.json', '.'),  # Global configuration file
    ('app_config.json', '.'),  # Application configuration file (default, runtime priority /etc)
    ('local_secrets.json.template', '.'),  # Local secrets template file
    ('setup_secrets.py', '.'),  # Sensitive configuration initialization script
    ('setup_first_deploy.py', '.'),  # First deployment setup script
    # Only include necessary pygments data, exclude large files
    *collect_data_files('pygments', include_py_files=False)  # Only include data files, not Python files
]

hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments'
]

a = Analysis(
    ['collabtrans/app.py'],  # Use forward slash, Windows also supports it
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-numpy-fix.py'],
    excludes=[
        # Large dependency packages
        "docling", "collabtrans.converter.x2md.converter_docling",
        "torch", "torchvision", "torchaudio",
        "transformers", "tokenizers", "sentencepiece",
        "easyocr", "cv2", "opencv-python",
        "scipy", "pandas", "matplotlib", "seaborn",
        "sklearn", "scikit-learn",
        "nltk", "spacy", "gensim", "jieba",
        "celery", "sqlalchemy",
        # Optional feature modules
        "collabtrans.converter.x2md.converter_docling",
        # Testing and development tools
        "pytest", "pytest-asyncio", "pytest-cov",
        "black", "flake8", "mypy",
        # Other large packages
        "jupyter", "ipython", "notebook",
        "tensorflow", "keras",
        "xgboost", "lightgbm",
        # numpy related (if causing compatibility issues)
        "numpy",
    ],
    noarchive=False,
    optimize=2,  # Enable Python bytecode optimization
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
    icon='CollabTrans.ico',  # Fixed as string
)