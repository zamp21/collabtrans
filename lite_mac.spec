# -*- mode: python ; coding: utf-8 -*-

# 导入 os 模块以更好地处理路径
import os
from PyInstaller.utils.hooks import collect_all

# --- 数据文件和二进制文件 ---
# 路径分隔符已更正为 '/'，这在所有平台上都更具兼容性
datas = [
    ('./docutranslate/static', 'docutranslate/static'),
    ('./docutranslate/template', 'docutranslate/template')
]
binaries = []
hiddenimports=['markdown.extensions.tables','pymdownx.arithmatex','pymdownx.superfences','pymdownx.highlight','pygments']

# 使用 collect_all 来收集依赖
# 这部分代码是跨平台的，无需修改
for i in ['pygments']:
    tmp_ret = collect_all(i)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

# --- 分析阶段 ---
a = Analysis(
    # 【修改 1】: 使用正斜杠 '/' 作为路径分隔符
    ['docutranslate/app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["docling","docutranslate.converter.x2md.converter_docling"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# --- EXE 和 COLLECT 阶段 ---
# EXE 仅创建 Unix 可执行文件
exe = EXE(
    pyz,
    a.scripts,
    [], # binaries 和 datas 移到下面的 BUNDLE/COLLECT 中
    [],
    name='DocuTranslate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    # 【修改 2】: 如果是 GUI 应用，建议设为 False
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2', # 推荐 'universal2' 以支持 Apple Silicon 和 Intel
    codesign_identity=None,
    entitlements_file=None,
)

# --- BUNDLE 阶段 (macOS 核心) ---
# 【修改 3】: 使用 BUNDLE 创建 .app 包，而不是单独的 EXE
# 这将生成一个标准的 macOS 应用程序
app = BUNDLE(
    exe,
    name='DocuTranslate.app',
    # 【修改 4】: 使用 .icns 格式的图标
    icon='DocuTranslate.icns',
    bundle_identifier='cc.xunbu.docutranslate', # 推荐设置一个唯一的包标识符
    info_plist={
        'NSHighResolutionCapable': 'True',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDisplayName': 'DocuTranslate',
        'CFBundleName': 'DocuTranslate',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0',
        'NSHumanReadableCopyright': 'Copyright © 2023 Your Name. All rights reserved.'
    }
)

# 将 a.datas 和 a.binaries 添加到 .app 包中
app.datas += a.datas
app.binaries += a.binaries