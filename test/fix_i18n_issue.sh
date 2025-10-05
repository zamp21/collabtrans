#!/bin/bash
# Script to fix missing i18n directory issue

echo "🔧 Fixing missing i18n directory issue"
echo "================================"

cd /mnt/2TDisk/workplace/collabtrans

# 1. Check necessary files and directories
echo "1. Checking necessary files and directories..."

# Check i18n directory
if [ -d "collabtrans/i18n" ]; then
    echo "✅ i18n directory exists"
    ls -la collabtrans/i18n/
else
    echo "❌ i18n directory does not exist, creating it..."
    mkdir -p collabtrans/i18n
    echo "✅ i18n directory created"
fi

# Check configuration files
if [ -f "global_config.json" ]; then
    echo "✅ global_config.json exists"
else
    echo "❌ global_config.json does not exist!"
    exit 1
fi

if [ -f "local_secrets.json.template" ]; then
    echo "✅ local_secrets.json.template exists"
else
    echo "❌ local_secrets.json.template does not exist!"
    exit 1
fi

# Check deployment scripts
if [ -f "setup_secrets.py" ]; then
    echo "✅ setup_secrets.py exists"
else
    echo "❌ setup_secrets.py does not exist!"
    exit 1
fi

if [ -f "setup_first_deploy.py" ]; then
    echo "✅ setup_first_deploy.py exists"
else
    echo "❌ setup_first_deploy.py does not exist!"
    exit 1
fi

# 2. Clean old build files
echo "2. Cleaning old build files..."
rm -rf dist/CollabTrans-*-linux
rm -rf build/deb/collabtrans*_*_amd64.deb

# 3. Rebuild all versions
echo "3. Rebuilding all versions..."

echo "Building lite version..."
./tools/build_deb.sh --lite

echo "Building full version..."
./tools/build_deb.sh --full

echo "Building balance version..."
./tools/build_deb.sh --balance

# 4. Check build results
echo "4. Checking build results..."
echo "📊 Built versions:"
ls -lh dist/CollabTrans-*-linux

echo "📦 Built DEB packages:"
ls -lh build/deb/collabtrans*_*_amd64.deb

echo ""
echo "🎉 All versions rebuilt successfully!"
echo ""
echo "📋 Testing suggestions:"
echo "1. Test lite version first: sudo dpkg -i build/deb/collabtrans_*_amd64.deb"
echo "2. Then test full version: sudo dpkg -i build/deb/collabtrans-full_*_amd64.deb"
echo "3. Finally test balance version: sudo dpkg -i build/deb/collabtrans-balance_*_amd64.deb"
