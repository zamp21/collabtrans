# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import docutranslate

datas = [
    ('./docutranslate/static', 'docutranslate/static'),
    ('./docutranslate/template', 'docutranslate/template')
]

# 只收集 pygments 的数据文件
datas += collect_data_files('pygments')

hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments'
]

a = Analysis(
    ['docutranslate/app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["docling","docutranslate.converter.x2md.converter_docling"],
    noarchive=False,
    target_arch='universal2',
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'DocuTranslate-{docutranslate.__version__}-mac',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    codesign_identity=None,
    entitlements_file=None,
    icon='DocuTranslate.icns',
)