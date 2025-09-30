# -*- mode: python ; coding: utf-8 -*-
# Balance版本：基于lite版本，但包含docling及其关联库
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_all
import collabtrans

# 收集docling相关数据
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
    # 包含pygments数据
    *collect_data_files('pygments', include_py_files=False)
]

# 收集docling相关资源
binaries = []
hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments'
]

# 收集docling相关依赖
try:
    docling_data, docling_binaries, docling_hidden = collect_all('docling')
    datas += docling_data
    binaries += docling_binaries
    hiddenimports += docling_hidden
    print("✅ 成功收集docling相关资源")
except Exception as e:
    print(f"⚠️ 收集docling资源时出错: {e}")

# 收集numpy相关资源（docling依赖）- 使用更安全的方式
try:
    import numpy
    numpy_data, numpy_binaries, numpy_hidden = collect_all('numpy')
    datas += numpy_data
    binaries += numpy_binaries
    # 添加更完整的numpy模块，确保兼容性
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
    print("✅ 成功收集numpy相关资源")
except Exception as e:
    print(f"⚠️ 收集numpy资源时出错: {e}")

# 收集scipy相关资源（docling依赖）
try:
    scipy_data, scipy_binaries, scipy_hidden = collect_all('scipy')
    datas += scipy_data
    binaries += scipy_binaries
    hiddenimports += scipy_hidden
    print("✅ 成功收集scipy相关资源")
except Exception as e:
    print(f"⚠️ 收集scipy资源时出错: {e}")

a = Analysis(
    ['collabtrans/app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),  # 去重
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-numpy-fix.py'],
    excludes=[
        # 排除最大的依赖包，但保留docling和MinerU相关
        # 注意：docling-ibm-models需要torch、transformers等，所以不能排除
        # "torch", "torchvision", "torchaudio",
        # "transformers", "tokenizers", "sentencepiece",
        "easyocr", "cv2", "opencv-python",
        "matplotlib", "seaborn",
        "sklearn", "scikit-learn",
        "nltk", "spacy", "gensim", "jieba",
        "celery", "sqlalchemy",
        # 测试和开发工具
        "pytest", "pytest-asyncio", "pytest-cov",
        "black", "flake8", "mypy",
        # 其他大包
        "jupyter", "ipython", "notebook",
        "tensorflow", "keras",
        "xgboost", "lightgbm",
        # 排除有问题的numpy测试模块和核心模块
        "numpy.tests", "numpy.testing",
        "numpy._pyinstaller", "numpy.f2py.tests",
        "numpy.ma.tests", "numpy.lib.tests",
        "numpy.core.tests", "numpy.random.tests",
        "numpy.linalg.tests", "numpy.fft.tests",
        "numpy.polynomial.tests", "numpy.matrixlib.tests",
        "numpy.typing.tests", "numpy.compat.tests",
        "numpy._core.tests", "numpy._typing.tests",
        # 排除有问题的numpy核心模块
        "numpy.core._add_newdocs",
        "numpy.core.machar",
        "numpy.core.umath_tests",
        "numpy._core._add_newdocs",
        "numpy.core._multiarray_umath",
        "numpy.core._multiarray_tests",
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
