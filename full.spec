# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all
import collabtrans

# 初始化列表
datas = []
binaries = []
hiddenimports = ['markdown.extensions.tables', 'pymdownx.arithmatex',
                'pymdownx.superfences', 'pymdownx.highlight', 'pygments']

# 先收集第三方包的资源
for package in ['easyocr', 'docling', 'pygments']:
    try:
        tmp_ret = collect_all(package)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Failed to collect resources for {package}: {e}")

# 然后添加您的自定义资源（避免重复）
custom_datas = [
    ('./.venv/Lib/site-packages/docling_parse/pdf_resources_v2', 'docling_parse/pdf_resources_v2'),
    ('./collabtrans/static', 'collabtrans/static'),
    ('./collabtrans/template', 'collabtrans/template')
]

# 避免添加重复的数据
for data in custom_datas:
    if data not in datas:
        datas.append(data)

a = Analysis(
    ['collabtrans/app.py'],  # 使用正斜杠
    pathex=[],  # 添加当前工作目录到 pathex
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),  # 去重
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'DocuTranslate_full-{collabtrans.__version__}-win',
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
    icon='DocuTranslate.ico',
)