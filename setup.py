#!/usr/bin/env python3
"""BITTU — Setup script for pip install and binary building."""
from setuptools import setup, find_packages

setup(
    name="bittu",
    version="2.0.0",
    description="BITTU — Grok-style terminal AI agent with Dream Mode ULTRA PRO",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="BITTU Team",
    url="https://github.com/cmyolo441-coder/notworking",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "textual>=0.40.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "bittu=zedpy.__main__:main",
            "bittu-tui=zedpy.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Code Generators",
    ],
)
