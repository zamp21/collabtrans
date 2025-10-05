# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import sys
from pathlib import Path

def resource_path(relative_path):
    """ Get absolute path of resources, suitable for development environment and PyInstaller packaged environment """
    try:
        base_path = Path(sys._MEIPASS)/"collabtrans"
    except Exception:
        base_path = Path(__file__).resolve().parent.parent # Development time
        # More robust development path (if your resources are relative to project root)
        # base_path = Path(os.path.abspath("."))
        # Or, if your static directory is always at the same level as app.py (development time)
        # base_path = Path(__file__).resolve().parent
    # print(f"base_path:{base_path}")
    return base_path / relative_path