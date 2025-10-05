#!/usr/bin/env python3
"""
CollabTrans configuration file management script
Used to manage /etc/collabtrans and local configuration files
"""

import os
import shutil
import json
from pathlib import Path
import argparse

def check_config_files():
    """Check configuration file status"""
    print("🔍 Checking configuration file status...")
    print("=" * 50)
    
    system_config = "/etc/collabtrans/global_config.json"
    system_secrets = "/etc/collabtrans/local_secrets.json"
    system_template = "/etc/collabtrans/local_secrets.json.template"
    
    local_config = "global_config.json"
    local_secrets = "local_secrets.json"
    local_template = "local_secrets.json.template"
    
    # Check executable program directory (if in packaged environment)
    import sys
    exe_dir = None
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        exe_config = os.path.join(exe_dir, "global_config.json")
        exe_secrets = os.path.join(exe_dir, "local_secrets.json")
        exe_template = os.path.join(exe_dir, "local_secrets.json.template")
    
    # Check system configuration files
    print("📁 System configuration files (/etc/collabtrans/):")
    if os.path.exists(system_config):
        print(f"  ✅ global_config.json exists")
    else:
        print(f"  ❌ global_config.json does not exist")
    
    if os.path.exists(system_secrets):
        print(f"  ✅ local_secrets.json exists")
    else:
        print(f"  ❌ local_secrets.json does not exist")
    
    if os.path.exists(system_template):
        print(f"  ✅ local_secrets.json.template exists")
    else:
        print(f"  ❌ local_secrets.json.template does not exist")
    
    # Check executable program directory configuration files (if in packaged environment)
    if exe_dir:
        print(f"\n📁 Executable program directory configuration files ({exe_dir}/):")
        if os.path.exists(exe_config):
            print(f"  ✅ global_config.json exists")
        else:
            print(f"  ❌ global_config.json does not exist")
        
        if os.path.exists(exe_secrets):
            print(f"  ✅ local_secrets.json exists")
        else:
            print(f"  ❌ local_secrets.json does not exist")
        
        if os.path.exists(exe_template):
            print(f"  ✅ local_secrets.json.template exists")
        else:
            print(f"  ❌ local_secrets.json.template does not exist")
    
    # Check local configuration files
    print("\n📁 Local configuration files:")
    if os.path.exists(local_config):
        print(f"  ✅ global_config.json exists")
    else:
        print(f"  ❌ global_config.json does not exist")
    
    if os.path.exists(local_secrets):
        print(f"  ✅ local_secrets.json exists")
    else:
        print(f"  ❌ local_secrets.json does not exist")
    
    if os.path.exists(local_template):
        print(f"  ✅ local_secrets.json.template exists")
    else:
        print(f"  ❌ local_secrets.json.template does not exist")
    
    # Display configuration file priority
    print("\n📋 Configuration file priority:")
    print("  1. /etc/collabtrans/ (system configuration)")
    if exe_dir:
        print(f"  2. {exe_dir}/ (executable program directory)")
    print("  3. ./ (current directory)")

def copy_to_system():
    """Copy local configuration files to system directory"""
    print("📋 Copying configuration files to system directory...")
    print("=" * 50)
    
    system_dir = "/etc/collabtrans"
    os.makedirs(system_dir, exist_ok=True)
    
    files_to_copy = [
        ("global_config.json", f"{system_dir}/global_config.json"),
        ("local_secrets.json.template", f"{system_dir}/local_secrets.json.template")
    ]
    
    for src, dst in files_to_copy:
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
                print(f"✅ Copied {src} -> {dst}")
            except PermissionError:
                print(f"❌ Insufficient permissions, cannot copy to {dst}")
                print(f"   Please run this script with sudo")
            except Exception as e:
                print(f"❌ Copy failed: {e}")
        else:
            print(f"⚠️  Source file {src} does not exist, skipping")

def copy_from_system():
    """Copy configuration files from system directory to local"""
    print("📋 Copying configuration files from system directory to local...")
    print("=" * 50)
    
    system_dir = "/etc/collabtrans"
    
    files_to_copy = [
        (f"{system_dir}/global_config.json", "global_config.json"),
        (f"{system_dir}/local_secrets.json.template", "local_secrets.json.template")
    ]
    
    for src, dst in files_to_copy:
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
                print(f"✅ Copied {src} -> {dst}")
            except Exception as e:
                print(f"❌ Copy failed: {e}")
        else:
            print(f"⚠️  Source file {src} does not exist, skipping")

def create_system_secrets():
    """Create system configuration files from template"""
    print("🔧 Creating system configuration files from template...")
    print("=" * 50)
    
    system_dir = "/etc/collabtrans"
    template_file = f"{system_dir}/local_secrets.json.template"
    secrets_file = f"{system_dir}/local_secrets.json"
    
    if not os.path.exists(template_file):
        print(f"❌ Template file {template_file} does not exist")
        return
    
    if os.path.exists(secrets_file):
        response = input(f"⚠️  Configuration file {secrets_file} already exists, overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Operation cancelled")
            return
    
    try:
        shutil.copy2(template_file, secrets_file)
        print(f"✅ Created {secrets_file}")
        print("💡 Please edit this file to set your API keys and admin password")
    except PermissionError:
        print(f"❌ Insufficient permissions, cannot create {secrets_file}")
        print("   Please run this script with sudo")
    except Exception as e:
        print(f"❌ Creation failed: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="CollabTrans configuration file management tool")
    parser.add_argument("action", choices=["check", "copy-to-system", "copy-from-system", "create-secrets"],
                       help="Operation type")
    
    args = parser.parse_args()
    
    print("🔧 CollabTrans configuration file management tool")
    print("=" * 50)
    
    if args.action == "check":
        check_config_files()
    elif args.action == "copy-to-system":
        copy_to_system()
    elif args.action == "copy-from-system":
        copy_from_system()
    elif args.action == "create-secrets":
        create_system_secrets()
    
    print("\n📚 Usage instructions:")
    print("1. check - Check configuration file status")
    print("2. copy-to-system - Copy local configuration files to system directory")
    print("3. copy-from-system - Copy configuration files from system directory to local")
    print("4. create-secrets - Create system configuration files from template")

if __name__ == "__main__":
    main()
