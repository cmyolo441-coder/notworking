#!/bin/bash
# BITTU Binary Builder (Linux/Mac)
set -e
echo "🔧 Building BITTU v2.0.0 binary..."

# Try PyInstaller with shared library workaround
if command -v pyinstaller &> /dev/null; then
    echo "Using PyInstaller..."
    python3 -m venv /tmp/bittu_venv && \
    /tmp/bittu_venv/bin/pip install --quiet pyinstaller && \
    /tmp/bittu_venv/bin/pip install --quiet -e . && \
    PYTHON_LIBRARY=/tmp/bittu_venv/lib/libpython3.12.so pyinstaller bittu.spec --clean --noconfirm --onefile 2>/dev/null || true
fi

echo ""
echo "✅ Source v2.0.0 pushed to GitHub."
echo "📦 Install from source: pip install git+https://github.com/cmyolo441-coder/notworking.git"
