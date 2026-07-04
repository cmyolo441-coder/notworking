#!/bin/bash
# BITTU Installer
# Quick install script for BITTU

set -e

echo "🚀 BITTU Installer"
echo "=================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "✅ Python version OK"
else
    echo "❌ Python 3.10+ required"
    exit 1
fi

echo ""

# Ask install method
echo "Select install method:"
echo "  1) pip install (recommended)"
echo "  2) Build binary"
echo "  3) Development mode"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "📦 Installing with pip..."
        pip install .
        echo ""
        echo "✅ Installed! Run with: bittu"
        ;;
    2)
        echo ""
        echo "📦 Building binary..."
        if ! command -v pyinstaller &> /dev/null; then
            echo "Installing PyInstaller..."
            pip install pyinstaller
        fi
        pyinstaller bittu.spec --clean --noconfirm
        echo ""
        echo "✅ Binary built: dist/bittu/"
        echo "Run with: ./dist/bittu/bittu"
        ;;
    3)
        echo ""
        echo "📦 Installing in dev mode..."
        pip install -e .
        echo ""
        echo "✅ Dev mode installed! Run with: bittu"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 BITTU installed successfully!"
echo ""
echo "Quick start:"
echo "  bittu                    # Launch TUI"
echo "  bittu --plain            # Plain REPL mode"
echo "  bittu -p 'hello'         # One-shot prompt"
echo ""
