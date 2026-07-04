#!/bin/bash
# BITTU Updater
# Pull latest updates from GitHub and reinstall

set -e

echo "🔄 BITTU Updater"
echo "================"
echo ""

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Install git first."
    exit 1
fi

# Find BITTU installation
BITTU_DIR=""
if [ -d "/workspaces/notworking" ]; then
    BITTU_DIR="/workspaces/notworking"
elif [ -d "$HOME/.bittu" ]; then
    BITTU_DIR="$HOME/.bittu"
elif command -v bittu &> /dev/null; then
    # Try to find where bittu is installed
    BITTU_PATH=$(which bittu)
    BITTU_DIR=$(dirname $(dirname "$BITTU_PATH"))
fi

if [ -z "$BITTU_DIR" ]; then
    echo "❌ BITTU not found. Install first:"
    echo "   pip install git+https://github.com/cmyolo441-coder/notworking.git"
    exit 1
fi

echo "📁 BITTU directory: $BITTU_DIR"
echo ""

# Pull latest changes
echo "📥 Pulling latest updates..."
cd "$BITTU_DIR"
git pull origin main

if [ $? -ne 0 ]; then
    echo "❌ Failed to pull updates"
    exit 1
fi

echo ""
echo "📦 Reinstalling..."
pip install -e . --quiet

if [ $? -ne 0 ]; then
    echo "❌ Failed to reinstall"
    exit 1
fi

echo ""
echo "✅ BITTU updated successfully!"
echo ""
echo "Current version:"
python3 -c "from zedpy import __version__; print(__version__)" 2>/dev/null || echo "v1.0.0"
echo ""
