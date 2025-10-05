# -*- mode: python ; coding: utf-8 -*-
# Balance version: Based on lite version, but includes docling and its associated libraries
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_all
import collabtrans

# Collect docling related data
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
    # Include pygments data
    *collect_data_files('pygments', include_py_files=False)
]

# Collect docling related resources
binaries = []
hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments'
]

# Collect docling related dependencies
try:
    docling_data, docling_binaries, docling_hidden = collect_all('docling')
    datas += docling_data
    binaries += docling_binaries
    hiddenimports += docling_hidden
    print("✅ Successfully collected docling related resources")
except Exception as e:
    print(f"⚠️ Error collecting docling resources: {e}")

# Collect numpy related resources (docling dependency) - use safer approach
try:
    import numpy
    numpy_data, numpy_binaries, numpy_hidden = collect_all('numpy')
    datas += numpy_data
    binaries += numpy_binaries
    # Add more complete numpy modules to ensure compatibility
    numpy_essential = [
        'numpy._core.multiarray',
        'numpy._core.umath',
        'numpy._core._multiarray_umath',
        'numpy._core.overrides',
        'numpy.core.multiarray',
        'numpy.core.umath',
        'numpy.core._multiarray_umath',
        'numpy.core.overrides',
        'numpy.core._add_newdocs',
        'numpy.core._dtype_ctypes',
        'numpy.core._internal',
        'numpy.core._methods',
        'numpy.core._type_aliases',
        'numpy.core.arrayprint',
        'numpy.core.defchararray',
        'numpy.core.fromnumeric',
        'numpy.core.function_base',
        'numpy.core.getlimits',
        'numpy.core.machar',
        'numpy.core.memmap',
        'numpy.core.records',
        'numpy.core.shape_base',
        'numpy.core.umath_tests'
    ]
    hiddenimports += numpy_essential
    print("✅ Successfully collected numpy related resources")
except Exception as e:
    print(f"⚠️ Error collecting numpy resources: {e}")

# Collect scipy related resources (docling dependency)
try:
    scipy_data, scipy_binaries, scipy_hidden = collect_all('scipy')
    datas += scipy_data
    binaries += scipy_binaries
    hiddenimports += scipy_hidden
    print("✅ Successfully collected scipy related resources")
except Exception as e:
    print(f"⚠️ Error collecting scipy resources: {e}")

a = Analysis(
    ['collabtrans/app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),  # Remove duplicates
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-numpy-fix.py'],
    excludes=[
        # Exclude largest dependency packages, but keep docling and MinerU related
        # Note: docling-ibm-models requires torch, transformers, etc., so cannot exclude
        # "torch", "torchvision", "torchaudio",
        # "transformers", "tokenizers", "sentencepiece",
        "easyocr", "cv2", "opencv-python",
        "matplotlib", "seaborn",
        "sklearn", "scikit-learn",
        "nltk", "spacy", "gensim", "jieba",
        "celery", "sqlalchemy",
        # Testing and development tools
        "pytest", "pytest-asyncio", "pytest-cov",
        "black", "flake8", "mypy",
        # Other large packages
        "jupyter", "ipython", "notebook",
        "tensorflow", "keras",
        "xgboost", "lightgbm",
        # Exclude problematic numpy test modules and core modules
        "numpy.tests", "numpy.testing",
        "numpy._pyinstaller", "numpy.f2py.tests",
        "numpy.ma.tests", "numpy.lib.tests",
        "numpy.core.tests", "numpy.random.tests",
        "numpy.linalg.tests", "numpy.fft.tests",
        "numpy.polynomial.tests", "numpy.matrixlib.tests",
        "numpy.typing.tests", "numpy.compat.tests",
        "numpy._core.tests", "numpy._typing.tests",
        # Exclude problematic numpy core modules
        "numpy.core._add_newdocs",
        "numpy.core.machar",
        "numpy.core.umath_tests",
        "numpy._core._add_newdocs",
        "numpy.core._multiarray_umath",
        "numpy.core._multiarray_tests",
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
    name=f'CollabTrans-balance-{collabtrans.__version__}-{platform_suffix}',
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
    icon='CollabTrans.ico',
)
