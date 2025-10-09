# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import collabtrans

datas = [
    ('./collabtrans/static', 'collabtrans/static'),
    ('./collabtrans/template', 'collabtrans/template'),
    ('./collabtrans/i18n', 'collabtrans/i18n'),  # Add i18n directory
    ('./collabtrans/static/favicon.ico', 'collabtrans/favicon.ico'),
    ('./global_config.json', '.'),  # Global configuration file
    ('./app_config.json', '.'),  # Application configuration file
    ('./local_secrets.json.template', '.'),  # Local secrets template file
    ('./local_config.json.template', '.'),  # Local configuration template file
    ('./local_users.json.template', '.'),  # Local users template file
    ('./collabtrans/config/templates/default_profile.json', 'collabtrans/config/templates/'),  # Default user profile template
    ('./setup_secrets.py', '.'),  # Sensitive configuration initialization script
    ('./setup_first_deploy.py', '.')  # First deployment setup script
    # Note: Redis config files are Windows-specific, not needed for macOS
]

# Only collect pygments data files
datas += collect_data_files('pygments')

hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments'
]

a = Analysis(
    ['collabtrans/app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["docling","collabtrans.converter.x2md.converter_docling"],
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
    name=f'DocuTranslate-{collabtrans.__version__}-mac',
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