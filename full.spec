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
    ('./collabtrans/template', 'collabtrans/template'),
    ('./collabtrans/i18n', 'collabtrans/i18n'),  # 添加i18n目录
    ('./collabtrans/static/favicon.ico', 'collabtrans/favicon.ico'),
    ('./global_config.json', '.'),  # 全局配置文件
    ('./app_config.json', '.'),  # 应用配置文件（默认，运行时优先 /etc）
    ('./local_secrets.json.template', '.'),  # 本地密钥模板文件
    ('./setup_secrets.py', '.'),  # 敏感配置初始化脚本
    ('./setup_first_deploy.py', '.')  # 首次部署设置脚本
]

# 避免添加重复的数据
for data in custom_datas:
    if data not in datas:
        datas.append(data)

# —— 同步 balance 版的 NumPy 兼容处理 ——
try:
    # 为确保冻结环境兼容性，补充 numpy 关键模块为隐藏导入
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
    ['collabtrans/app.py'],  # 使用正斜杠
    pathex=[os.getcwd()],  # 添加当前工作目录到 pathex，提高资源发现成功率
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),  # 去重
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-numpy-fix.py'],
    # 同步 balance 的 numpy 排除策略，避免已知崩溃点
    excludes=[
        # numpy 测试/打包辅助
        'numpy.tests','numpy.testing','numpy._pyinstaller','numpy.f2py.tests',
        'numpy.ma.tests','numpy.lib.tests','numpy.core.tests','numpy.random.tests',
        'numpy.linalg.tests','numpy.fft.tests','numpy.polynomial.tests',
        'numpy.matrixlib.tests','numpy.typing.tests','numpy.compat.tests',
        'numpy._core.tests','numpy._typing.tests',
        # 有问题的 numpy 核心模块
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