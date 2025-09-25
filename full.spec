# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
import collabtrans

# 初始化列表
datas = []
binaries = []
hiddenimports = ['markdown.extensions.tables', 'pymdownx.arithmatex',
                'pymdownx.superfences', 'pymdownx.highlight', 'pygments']

# 先收集第三方包的资源（存在即收集）
for package in ['easyocr', 'docling', 'pygments']:
    try:
        tmp_ret = collect_all(package)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Failed to collect resources for {package}: {e}")

"""
尽可能以跨平台方式定位 docling_parse/pdf_resources_v2。
Windows 的 .venv/Lib 路径在 Linux/macOS 上不可用，因此改为动态发现。
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

# 然后添加您的自定义资源（避免重复）
custom_datas = [
    ('./collabtrans/static', 'collabtrans/static'),
    ('./collabtrans/template', 'collabtrans/template')
]

# 避免添加重复的数据
for data in custom_datas:
    if data not in datas:
        datas.append(data)

a = Analysis(
    ['collabtrans/app.py'],  # 使用正斜杠
    pathex=[os.getcwd()],  # 添加当前工作目录到 pathex，提高资源发现成功率
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