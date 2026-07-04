.PHONY: build install clean test lint help

# BITTU Makefile
# Build, install, and manage BITTU binary

PYTHON ?= python3
PIP ?= pip3
PYINSTALLER ?= pyinstaller

# Default target
all: build

help:
	@echo "BITTU Build System"
	@echo "=================="
	@echo ""
	@echo "Targets:"
	@echo "  make build      - Build standalone binary"
	@echo "  make install    - Install as Python package"
	@echo "  make install-bin - Install binary to /usr/local/bin"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linter"
	@echo "  make dev        - Install in development mode"
	@echo ""

# Build binary with PyInstaller
build:
	@echo "📦 Building BITTU binary..."
	$(PYINSTALLER) bittu.spec --clean --noconfirm
	@echo "✅ Binary built: dist/bittu/"

# Install as Python package
install:
	@echo "📦 Installing BITTU..."
	$(PIP) install .
	@echo "✅ Installed! Run with: bittu"

# Install in development mode
dev:
	@echo "📦 Installing BITTU (dev mode)..."
	$(PIP) install -e .
	@echo "✅ Installed in dev mode!"

# Install binary to system path
install-bin: build
	@echo "📦 Installing binary to /usr/local/bin..."
	cp dist/bittu/bittu /usr/local/bin/
	@echo "✅ Installed! Run with: bittu"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning..."
	rm -rf build/ dist/ *.spec.bak __pycache__ zedpy/__pycache__
	@echo "✅ Cleaned!"

# Run tests
test:
	@echo "🧪 Running tests..."
	$(PYTHON) -m pytest test_*.py -v

# Run linter
lint:
	@echo "🔍 Running linter..."
	$(PYTHON) -m ruff check zedpy/

# Format code
format:
	@echo "✨ Formatting code..."
	$(PYTHON) -m ruff format zedpy/

# Create distribution
dist: clean
	@echo "📦 Creating distribution..."
	$(PYTHON) -m build
	@echo "✅ Distribution created in dist/"

# Watch mode (rebuild on changes)
watch:
	@echo "👀 Watching for changes..."
	@while true; do \
		inotifywait -qre modify . --include='*.py'; \
		make build; \
	done
