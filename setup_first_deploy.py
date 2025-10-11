#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CollabTrans first deployment setup script
Automatically complete basic configuration required for first deployment
"""

import os
import shutil
import json
import secrets
import string
from pathlib import Path


def generate_random_key(length=32):
    """Generate random key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def setup_first_deploy():
    """First deployment setup"""
    print("🚀 CollabTrans first deployment setup")
    print("=" * 50)
    
    # 1. Create local_secrets.json
    local_secrets_path = "local_secrets.json"
    local_secrets_template_path = "local_secrets.json.template"
    
    if not os.path.exists(local_secrets_path) and os.path.exists(local_secrets_template_path):
        try:
            shutil.copy2(local_secrets_template_path, local_secrets_path)
            print("✅ Created local_secrets.json configuration file")
            
            # Generate random key
            with open(local_secrets_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Remove template comment fields to avoid entering production files
            for k in ['_comment', '_warning']:
                if k in config:
                    config.pop(k, None)
            
            # Authentication is now managed by unified user storage and local_config.json
            # No need to generate auth_secrets
            
            with open(local_secrets_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print("✅ Generated secrets configuration")
            
        except Exception as e:
            print(f"❌ Failed to create local_secrets.json: {e}")
    else:
        print("ℹ️  local_secrets.json already exists, skipping creation")
    
    # 2. Check and create necessary directories
    directories = ['logs', 'output', 'certs', 'glossaries', 'user_profiles']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created directory: {directory}")
    
    # 3. Check configuration files
    config_files = ['local_config.json', 'global_config.json', 'app_config.json']
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ Configuration file exists: {config_file}")
        else:
            print(f"⚠️  Configuration file missing: {config_file}")
    
    # 4. Display next steps guide
    print("\n" + "=" * 50)
    print("🎉 First deployment setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit local_secrets.json file to set your API keys")
    print("2. Install Redis service (for session management)")
    print("3. Start CollabTrans service")
    print("\n🔧 Startup command:")
    print("   .venv\\Scripts\\python.exe -m collabtrans.cli -i")
    print("\n🌐 Access URL:")
    print("   http://127.0.0.1:8010")
    print("\n👤 Default login information:")
    print("   Username: admin")
    print("   Password: [Set via unified user storage]")
    print("\n📚 For more information, check the documents in the doc/ directory")


if __name__ == "__main__":
    setup_first_deploy()
