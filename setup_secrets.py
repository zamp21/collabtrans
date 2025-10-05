#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

"""
Sensitive configuration initialization script
Used to set API keys and other sensitive information during first deployment
"""

import json
import os
import sys
from pathlib import Path

def main():
    """Main function"""
    print("🔐 DocuTranslate sensitive configuration initialization")
    print("=" * 50)
    
    # Check if sensitive configuration file already exists
    secrets_file = Path("local_secrets.json")
    if secrets_file.exists():
        print(f"⚠️  Sensitive configuration file {secrets_file} already exists")
        response = input("Do you want to reconfigure? (y/N): ").strip().lower()
        if response != 'y':
            print("Configuration cancelled")
            return
    
    # Create configuration template
    template_file = Path("local_secrets.json.template")
    if not template_file.exists():
        print(f"❌ Template file {template_file} does not exist")
        return
    
    print("\n📋 Please configure the following sensitive information (press Enter to skip):")
    print("=" * 50)
    
    # Read template
    with open(template_file, 'r', encoding='utf-8') as f:
        secrets = json.load(f)
    
    # Configure API keys (supports new structure { key, configured } and compatible with old string structure)
    print("\n🔑 API key configuration:")
    api_keys = secrets.get("platform_api_keys", {})
    for platform, placeholder in list(api_keys.items()):
        # Normalize to object structure
        if isinstance(placeholder, str):
            placeholder_obj = {"key": placeholder, "configured": bool(placeholder and not placeholder.startswith("your-"))}
            api_keys[platform] = placeholder_obj
        else:
            placeholder_obj = placeholder or {"key": "", "configured": False}

        key_placeholder = placeholder_obj.get("key") or ""
        # Only prompt for input when it's a template placeholder
        if isinstance(key_placeholder, str) and key_placeholder.startswith("your-"):
            current_value = input(f"  {platform}: ").strip()
            if current_value:
                api_keys[platform]["key"] = current_value
                api_keys[platform]["configured"] = True
            else:
                # Keep unconfigured
                api_keys[platform]["key"] = ""
                api_keys[platform]["configured"] = False
    
    # Configure MinerU token (supports new structure { key, configured } and compatible with old string structure)
    print("\n🔧 MinerU token configuration:")
    mineru_entry = secrets.get("translator_mineru_token")
    if isinstance(mineru_entry, dict):
        current_placeholder = mineru_entry.get("key") or ""
    else:
        current_placeholder = mineru_entry or ""

    mineru_token = input("  MinerU Token: ").strip()
    if isinstance(mineru_entry, dict):
        secrets["translator_mineru_token"]["key"] = mineru_token if mineru_token else ""
        secrets["translator_mineru_token"]["configured"] = bool(mineru_token)
    else:
        # Fallback: use new structure
        secrets["translator_mineru_token"] = {"key": mineru_token if mineru_token else "", "configured": bool(mineru_token)}
    
    # Configure authentication sensitive information
    print("\n🔐 Authentication sensitive information configuration:")
    auth_secrets = secrets.get("auth_secrets", {})
    
    # Default password
    default_password = input("  Default admin password (default: admin123): ").strip()
    if default_password:
        auth_secrets["default_password"] = default_password
    else:
        auth_secrets["default_password"] = "admin123"
    
    # Session key
    session_secret = input("  Session key (default: auto-generated): ").strip()
    if session_secret:
        auth_secrets["session_secret_key"] = session_secret
    else:
        import secrets as secrets_module
        auth_secrets["session_secret_key"] = secrets_module.token_urlsafe(32)
        print(f"    Auto-generated session key: {auth_secrets['session_secret_key'][:8]}...")
    
    # Redis password
    redis_password = input("  Redis password (optional): ").strip()
    if redis_password:
        auth_secrets["redis_password"] = redis_password
    else:
        auth_secrets["redis_password"] = None
    
    # Save configuration
    try:
        with open(secrets_file, 'w', encoding='utf-8') as f:
            json.dump(secrets, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Sensitive configuration saved to: {secrets_file}")
        print("🔒 This file contains sensitive information, do not commit to git repository")
        
        # Set file permissions (owner read/write only)
        os.chmod(secrets_file, 0o600)
        print("🔐 File permissions set to owner read/write only")
        
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")
        return
    
    print("\n📝 Configuration summary:")
    print("=" * 50)
    
    # Count configured API keys (adapted to new structure)
    configured_keys = 0
    total_keys = len(api_keys)
    for val in api_keys.values():
        if isinstance(val, dict):
            if val.get("configured") and (val.get("key") or "").strip():
                configured_keys += 1
        else:
            if val and str(val).strip():
                configured_keys += 1
    print(f"  API keys: {configured_keys}/{total_keys} configured")
    
    # Display other configuration status
    mt = secrets.get('translator_mineru_token')
    if isinstance(mt, dict):
        mineru_configured = bool(mt.get('configured') and (mt.get('key') or '').strip())
    else:
        mineru_configured = bool(mt and str(mt).strip())
    print(f"  MinerU token: {'configured' if mineru_configured else 'not configured'}")
    print(f"  Default password: {'configured' if auth_secrets.get('default_password') else 'not configured'}")
    print(f"  Session key: {'configured' if auth_secrets.get('session_secret_key') else 'not configured'}")
    print(f"  Redis password: {'configured' if auth_secrets.get('redis_password') else 'not configured'}")
    
    print("\n🚀 Configuration completed! You can now start the DocuTranslate service")
    print("💡 Tip: After admin login, you can continue configuring API keys in the web interface")

if __name__ == "__main__":
    main()
