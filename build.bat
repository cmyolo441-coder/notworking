@echo off
REM BITTU Binary Builder for Windows
REM Build standalone binary for Windows

echo 🔧 BITTU Binary Builder
echo ======================
echo.

REM Check if PyInstaller is installed
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Clean previous builds
echo 🧹 Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build binary
echo 📦 Building binary...
pyinstaller bittu.spec --clean --noconfirm

REM Check if build succeeded
if exist dist\bittu\bittu.exe (
    echo.
    echo ✅ Build successful!
    echo.
    echo 📁 Binary location: dist\bittu\
    echo.
    echo To run:
    echo   dist\bittu\bittu.exe
    echo.
    echo To install globally:
    echo   copy dist\bittu\bittu.exe C:\Windows\System32\
    echo.
) else (
    echo ❌ Build failed!
    exit /b 1
)

pause
