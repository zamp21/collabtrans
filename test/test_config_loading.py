#!/usr/bin/env python3
"""
Test configuration file loading logic
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

def test_config_loading():
    """Test configuration file loading logic"""
    print("🧪 Testing configuration file loading logic")
    print("=" * 50)
    
    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Temporary test directory: {temp_dir}")
        
        # Create test directory structure
        system_dir = os.path.join(temp_dir, "etc", "collabtrans")
        exe_dir = os.path.join(temp_dir, "opt", "collabtrans")
        local_dir = os.path.join(temp_dir, "local")
        
        os.makedirs(system_dir, exist_ok=True)
        os.makedirs(exe_dir, exist_ok=True)
        os.makedirs(local_dir, exist_ok=True)
        
        # Create test configuration files
        test_config = '{"test": "config", "version": "1.0"}'
        
        # Test scenario 1: Only system configuration
        print("\n🔍 Test scenario 1: Only system configuration")
        system_config = os.path.join(system_dir, "global_config.json")
        with open(system_config, 'w') as f:
            f.write('{"source": "system", "test": "system_config"}')
        
        # Simulate system configuration loading
        if os.path.exists(system_config):
            print(f"✅ System configuration exists: {system_config}")
            with open(system_config, 'r') as f:
                config = f.read()
                print(f"   Content: {config}")
        else:
            print(f"❌ System configuration does not exist: {system_config}")
        
        # Test scenario 2: System configuration + executable program configuration
        print("\n🔍 Test scenario 2: System configuration + executable program configuration")
        exe_config = os.path.join(exe_dir, "global_config.json")
        with open(exe_config, 'w') as f:
            f.write('{"source": "executable", "test": "exe_config"}')
        
        # Simulate priority loading
        if os.path.exists(system_config):
            print(f"✅ Priority use system configuration: {system_config}")
            with open(system_config, 'r') as f:
                config = f.read()
                print(f"   Content: {config}")
        elif os.path.exists(exe_config):
            print(f"✅ Use executable program configuration: {exe_config}")
            with open(exe_config, 'r') as f:
                config = f.read()
                print(f"   Content: {config}")
        
        # Test scenario 3: Only executable program configuration
        print("\n🔍 Test scenario 3: Only executable program configuration")
        os.remove(system_config)  # Remove system configuration
        
        if os.path.exists(system_config):
            print(f"✅ Use system configuration: {system_config}")
        elif os.path.exists(exe_config):
            print(f"✅ Use executable program configuration: {exe_config}")
            with open(exe_config, 'r') as f:
                config = f.read()
                print(f"   Content: {config}")
        else:
            print("❌ No configuration file found")
        
        # Test scenario 4: Only local configuration
        print("\n🔍 Test scenario 4: Only local configuration")
        os.remove(exe_config)  # Remove executable program configuration
        local_config = os.path.join(local_dir, "global_config.json")
        with open(local_config, 'w') as f:
            f.write('{"source": "local", "test": "local_config"}')
        
        # Switch to local directory
        original_cwd = os.getcwd()
        os.chdir(local_dir)
        
        if os.path.exists(system_config):
            print(f"✅ Use system configuration: {system_config}")
        elif os.path.exists(exe_config):
            print(f"✅ Use executable program configuration: {exe_config}")
        elif os.path.exists("global_config.json"):
            print(f"✅ Use local configuration: global_config.json")
            with open("global_config.json", 'r') as f:
                config = f.read()
                print(f"   Content: {config}")
        else:
            print("❌ No configuration file found")
        
        os.chdir(original_cwd)
        
        # Test scenario 5: No configuration files
        print("\n🔍 Test scenario 5: No configuration files")
        os.remove(local_config)
        
        if os.path.exists(system_config):
            print(f"✅ Use system configuration: {system_config}")
        elif os.path.exists(exe_config):
            print(f"✅ Use executable program configuration: {exe_config}")
        elif os.path.exists("global_config.json"):
            print(f"✅ Use local configuration: global_config.json")
        else:
            print("❌ No configuration file found, using empty configuration")
    
    print("\n🎉 Configuration file loading logic test completed!")

def test_pyinstaller_detection():
    """Test PyInstaller environment detection"""
    print("\n🔍 Testing PyInstaller environment detection")
    print("=" * 50)
    
    # Check current environment
    if getattr(sys, 'frozen', False):
        print("✅ Currently running in PyInstaller packaged environment")
        print(f"   Executable file path: {sys.executable}")
        print(f"   Executable file directory: {os.path.dirname(sys.executable)}")
    else:
        print("ℹ️  Currently running in development environment")
        print(f"   Python interpreter path: {sys.executable}")
        print(f"   Current working directory: {os.getcwd()}")

if __name__ == "__main__":
    test_config_loading()
    test_pyinstaller_detection()
