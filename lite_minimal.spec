# -*- mode: python ; coding: utf-8 -*-
# Minimal Lite version configuration - only includes core functionality
import os
import sys
from PyInstaller.utils.hooks import collect_data_files
import collabtrans

# Minimal data files
datas = [
    ('collabtrans/static', 'collabtrans/static'),
    ('collabtrans/template', 'collabtrans/template'),
    ('collabtrans/i18n', 'collabtrans/i18n'),  # Add i18n directory
    ('collabtrans/static/favicon.ico', 'collabtrans/favicon.ico'),
    ('global_config.json', '.'),  # Global configuration file
    ('app_config.json', '.'),  # Application configuration file
    ('local_secrets.json.template', '.'),  # Local secrets template file
    ('local_config.json.template', '.'),  # Local configuration template file
    ('local_users.json.template', '.'),  # Local users template file
    ('collabtrans/config/templates/default_profile.json', 'collabtrans/config/templates/'),  # Default user profile template
    ('setup_secrets.py', '.'),  # Sensitive configuration initialization script
    ('setup_first_deploy.py', '.'),  # First deployment setup script
    # Redis executable and configuration files (Windows only)
    ('3rdParty/windows/Redis-x64-3.0.504/redis-server.exe', '3rdParty/windows/Redis-x64-3.0.504/'),
    ('3rdParty/windows/Redis-x64-3.0.504/redis.windows.conf', '3rdParty/windows/Redis-x64-3.0.504/'),
    ('3rdParty/windows/Redis-x64-3.0.504/redis.windows-service.conf', '3rdParty/windows/Redis-x64-3.0.504/'),
    # Exclude pygments large data files
]

# Minimal hidden imports
hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    # Do not include pygments to reduce size
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
        # All large dependency packages
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
        # Exclude pygments to reduce size
        "pygments",
        # Exclude some optional features
        "collabtrans.converter.x2xlsx",
        "collabtrans.exporter.epub",
        "collabtrans.exporter.srt",
        # Exclude some large utility modules
        "collabtrans.utils.redis_manager",  # If Redis functionality is not needed
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
    name=f'CollabTrans-minimal-{collabtrans.__version__}-{platform_suffix}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Enable symbol stripping
    upx=True,    # Enable UPX compression
    upx_exclude=[],  # Can exclude certain files from UPX compression
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='CollabTrans.ico',
)
