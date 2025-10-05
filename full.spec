# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
import collabtrans

# Initialize lists
datas = []
binaries = []
hiddenimports = ['markdown.extensions.tables', 'pymdownx.arithmatex',
                'pymdownx.superfences', 'pymdownx.highlight', 'pygments']

# First collect third-party package resources (collect if exists)
for package in ['easyocr', 'docling', 'pygments']:
    try:
        tmp_ret = collect_all(package)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Failed to collect resources for {package}: {e}")

"""
Locate docling_parse/pdf_resources_v2 in a cross-platform way as much as possible.
Windows .venv/Lib path is not available on Linux/macOS, so changed to dynamic discovery.
"""
try:
    import importlib.util
    spec = importlib.util.find_spec('docling_parse')
    if spec and spec.origin:
        base_dir = Path(spec.origin).parent
        res_dir = base_dir / 'pdf_resources_v2'
        if res_dir.exists():
            datas.append((str(res_dir), 'docling_parse/pdf_resources_v2'))
except Exception as _e:
    print(f"Warning: Failed to detect docling_parse resources dynamically: {_e}")

# Then add your custom resources (avoid duplicates)
custom_datas = [
    ('./collabtrans/static', 'collabtrans/static'),
    ('./collabtrans/template', 'collabtrans/template'),
    ('./collabtrans/i18n', 'collabtrans/i18n'),  # Add i18n directory
    ('./collabtrans/static/favicon.ico', 'collabtrans/favicon.ico'),
    ('./global_config.json', '.'),  # Global configuration file
    ('./app_config.json', '.'),  # Application configuration file (default, runtime priority /etc)
    ('./local_secrets.json.template', '.'),  # Local secrets template file
    ('./setup_secrets.py', '.'),  # Sensitive configuration initialization script
    ('./setup_first_deploy.py', '.')  # First deployment setup script
]

# Avoid adding duplicate data
for data in custom_datas:
    if data not in datas:
        datas.append(data)

# —— Sync balance version NumPy compatibility handling ——
try:
    # To ensure frozen environment compatibility, supplement numpy key modules as hidden imports
    numpy_essential = [
        'numpy._core.multiarray',
        'numpy._core.umath',
        'numpy._core._multiarray_umath',
        'numpy._core.overrides',
        'numpy.core.multiarray',
        'numpy.core.umath',
        'numpy.core._multiarray_umath',
        'numpy.core.overrides',
    ]
    hiddenimports = list(set(hiddenimports + numpy_essential))
except Exception as _e:
    print(f"Warning: failed to add numpy essential hiddenimports: {_e}")

a = Analysis(
    ['collabtrans/app.py'],  # Use forward slash
    pathex=[os.getcwd()],  # Add current working directory to pathex, improve resource discovery success rate
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),  # Remove duplicates
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-numpy-fix.py'],
    # Sync balance numpy exclusion strategy, avoid known crash points
    excludes=[
        # numpy testing/packaging assistance
        'numpy.tests','numpy.testing','numpy._pyinstaller','numpy.f2py.tests',
        'numpy.ma.tests','numpy.lib.tests','numpy.core.tests','numpy.random.tests',
        'numpy.linalg.tests','numpy.fft.tests','numpy.polynomial.tests',
        'numpy.matrixlib.tests','numpy.typing.tests','numpy.compat.tests',
        'numpy._core.tests','numpy._typing.tests',
        # Problematic numpy core modules
        'numpy.core._add_newdocs','numpy.core.machar','numpy.core.umath_tests',
        'numpy._core._add_newdocs','numpy.core._multiarray_umath','numpy.core._multiarray_tests',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

platform_suffix = 'win' if sys.platform.startswith('win') else ('mac' if sys.platform == 'darwin' else 'linux')

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'CollabTrans_full-{collabtrans.__version__}-{platform_suffix}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='CollabTrans.ico',
)