#!/usr/bin/env python3
"""
Script to verify if configuration files exist
"""
import os
import json
import sys
from pathlib import Path

def verify_config_files():
    """Verify if necessary configuration files exist and are valid"""
    print("🔍 Verifying configuration files...")
    
    # List of files to check
    required_files = [
        "global_config.json",
        "local_secrets.json.template",
        "setup_secrets.py",
        "setup_first_deploy.py"
    ]
    
    # List of directories to check
    required_dirs = [
        "collabtrans/i18n",
        "collabtrans/static",
        "collabtrans/template"
    ]
    
    all_good = True
    
    # Check files
    json_files = ["global_config.json", "local_secrets.json.template"]
    python_files = ["setup_secrets.py", "setup_first_deploy.py"]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
            # Only validate format for JSON files
            if file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    print(f"   ✅ {file_path} JSON format is valid")
                except json.JSONDecodeError as e:
                    print(f"   ❌ {file_path} JSON format is invalid: {e}")
                    all_good = False
                except Exception as e:
                    print(f"   ⚠️ {file_path} read error: {e}")
            elif file_path in python_files:
                print(f"   ✅ {file_path} Python script file")
        else:
            print(f"❌ {file_path} does not exist")
            all_good = False
    
    # Check directories
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print(f"✅ {dir_path}/ directory exists")
            # List directory contents
            try:
                files = os.listdir(dir_path)
                print(f"   Contains {len(files)} files/directories")
                if len(files) > 0:
                    print(f"   Examples: {files[:3]}{'...' if len(files) > 3 else ''}")
            except Exception as e:
                print(f"   ⚠️ Unable to read directory contents: {e}")
        else:
            print(f"❌ {dir_path}/ directory does not exist")
            all_good = False
    
    # Check i18n directory contents
    i18n_dir = Path("collabtrans/i18n")
    if i18n_dir.exists():
        i18n_files = list(i18n_dir.glob("*.json"))
        print(f"📁 i18n directory contains {len(i18n_files)} JSON files:")
        for file in i18n_files:
            print(f"   - {file.name}")
    
    return all_good

def main():
    """Main function"""
    print("🔧 CollabTrans configuration file verification tool")
    print("=" * 50)
    
    # Switch to project root directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Verify configuration files
    if verify_config_files():
        print("\n🎉 All configuration files verified successfully!")
        print("✅ Ready to start building")
        return 0
    else:
        print("\n❌ Configuration file verification failed!")
        print("Please check missing files or directories")
        return 1

if __name__ == "__main__":
    sys.exit(main())
