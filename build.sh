#!/bin/bash
# BITTU Binary Builder
# Build standalone binary for current platform

set -e

echo "🔧 BITTU Binary Builder"
echo "======================"
echo ""

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.spec.bak

# Build binary
echo "📦 Building binary..."
pyinstaller bittu.spec --clean --noconfirm

# Check if build succeeded
if [ -f dist/bittu/bittu ] || [ -f dist/bittu/bittu.exe ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "📁 Binary location: dist/bittu/"
    echo ""
    echo "To run:"
    echo "  ./dist/bittu/bittu              # Linux/Mac"
    echo "  dist/bittu\\bittu.exe            # Windows"
    echo ""
    echo "To install globally:"
    echo "  cp dist/bittu/bittu /usr/local/bin/"
    echo ""
else
    echo "❌ Build failed!"
    exit 1
fi
