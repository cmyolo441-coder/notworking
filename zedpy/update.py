#!/usr/bin/env python3
"""BITTU Self-Update Command.

Usage:
    bittu --update
    python -m zedpy --update

This will pull the latest changes from GitHub and reinstall BITTU.
"""
from __future__ import annotations
import os
import subprocess
import sys


def update() -> int:
    """Pull latest updates from GitHub and reinstall."""
    print("🔄 BITTU Updater")
    print("=" * 40)
    print()
    
    # Check if git is available
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Git not found. Install git first.")
        return 1
    
    # Find BITTU directory (current installation)
    bittu_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if we're in a git repo
    git_dir = os.path.join(bittu_dir, ".git")
    if not os.path.exists(git_dir):
        print("❌ Not a git installation.")
        print("   Reinstall with:")
        print("   pip install git+https://github.com/cmyolo441-coder/notworking.git")
        return 1
    
    print(f"📁 BITTU directory: {bittu_dir}")
    print()
    
    # Pull latest changes
    print("📥 Pulling latest updates...")
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=bittu_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to pull updates: {result.stderr}")
            return 1
        print(result.stdout)
    except Exception as e:
        print(f"❌ Error pulling updates: {e}")
        return 1
    
    # Reinstall
    print()
    print("📦 Reinstalling...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
            cwd=bittu_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to reinstall: {result.stderr}")
            return 1
    except Exception as e:
        print(f"❌ Error reinstalling: {e}")
        return 1
    
    print()
    print("✅ BITTU updated successfully!")
    print()
    
    # Show version
    try:
        from zedpy import __version__
        print(f"Current version: {__version__}")
    except ImportError:
        print("Current version: v1.0.0")
    
    return 0


if __name__ == "__main__":
    sys.exit(update())
