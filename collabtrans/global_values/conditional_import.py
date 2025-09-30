# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import importlib

available_packages={}

def conditional_import(packagename,alias=None):
    try:
        imported= importlib.import_module(packagename)
        if alias:
            globals()[alias]=imported
        else:
            globals()[packagename]=imported
        available_packages[packagename]=True
        return True
    except ImportError:
        available_packages[packagename]=False
        return False

# 在PyInstaller环境中，如果docling被排除，直接设置为False
try:
    DOCLING_EXIST=conditional_import("docling")
except Exception:
    # 如果导入失败（比如在lite版本中），设置为False
    DOCLING_EXIST=False
