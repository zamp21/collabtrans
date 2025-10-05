#!/bin/bash
# Build CollabTrans balance version

echo "🔧 Building CollabTrans balance version"
echo "================================"

cd /mnt/2TDisk/workplace/collabtrans

# 1. Clean old build files
echo "1. Cleaning old build files..."
rm -rf dist/CollabTrans-balance-*-linux
rm -rf build/deb/collabtrans-balance_*_amd64.deb

# 2. Build balance version
echo "2. Building balance version..."
./tools/build_deb.sh --balance

# 3. Check build results
echo "3. Checking build results..."
if [ -f "build/deb/collabtrans-balance_"*"_amd64.deb" ]; then
    echo "✅ Balance version built successfully!"
    ls -lh build/deb/collabtrans-balance_*_amd64.deb
    echo ""
    echo "📋 Installation command:"
    echo "sudo dpkg -i build/deb/collabtrans-balance_*_amd64.deb"
    echo ""
    echo "📋 Start service:"
    echo "sudo systemctl start collabtrans-balance"
    echo "sudo systemctl enable collabtrans-balance"
    echo ""
    echo "📋 Check status:"
    echo "sudo systemctl status collabtrans-balance"
else
    echo "❌ Balance version build failed!"
    exit 1
fi

echo ""
echo "🎉 Balance version build completed!"
echo ""
echo "📊 Balance version features:"
echo "- Includes docling support (PDF parsing)"
echo "- Includes MinerU support (PDF parsing)"
echo "- Includes numpy and scipy (docling dependencies)"
echo "- Excludes torch, transformers and other heavy dependencies"
echo "- Smaller than full version, more features than lite version"
