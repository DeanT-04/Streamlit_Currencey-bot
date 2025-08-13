#!/usr/bin/env python3
"""Validation script to check if the project setup is working correctly."""

import sys
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.10 or higher."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(
            f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible"
        )
        return True
    else:
        print(
            f"❌ Python 3.10+ required. Current: {version.major}.{version.minor}.{version.micro}"
        )
        return False


def check_project_structure():
    """Check if project directory structure exists."""
    required_dirs = ["src/backend", "src/frontend", "src/tests", "docs"]

    required_files = [
        "requirements.txt",
        ".env.example",
        "pyproject.toml",
        "setup_env.sh",
        "setup_env.bat",
        "src/backend/__init__.py",
        "src/backend/config.py",
        "src/backend/utils.py",
        "src/tests/test_config.py",
        "src/tests/test_utils.py",
    ]

    all_good = True

    for directory in required_dirs:
        if Path(directory).exists():
            print(f"✅ Directory {directory} exists")
        else:
            print(f"❌ Directory {directory} missing")
            all_good = False

    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ File {file_path} exists")
        else:
            print(f"❌ File {file_path} missing")
            all_good = False

    return all_good


def check_imports():
    """Check if core modules can be imported."""
    try:
        from src.backend.config import ConfigManager, get_config_manager
        from src.backend.utils import validate_currency_pair, format_currency

        print("✅ Core modules can be imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def check_basic_functionality():
    """Test basic functionality without requiring environment variables."""
    try:
        from src.backend.utils import (
            validate_currency_pair,
            format_currency,
            calculate_percentage,
        )

        # Test utility functions
        assert validate_currency_pair("EURUSD") == True
        assert validate_currency_pair("invalid") == False
        assert format_currency(123.45) == "USD 123.45"
        assert calculate_percentage(25, 100) == 25.0

        print("✅ Basic functionality tests passed")
        return True
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False


def main():
    """Run all validation checks."""
    print("🚀 Validating Pocket Option Trading Bot setup...\n")

    checks = [
        ("Python Version", check_python_version),
        ("Project Structure", check_project_structure),
        ("Module Imports", check_imports),
        ("Basic Functionality", check_basic_functionality),
    ]

    all_passed = True

    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        if not check_func():
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All validation checks passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Configure environment: cp .env.example .env")
        print("3. Edit .env with your API keys")
        print("4. Run tests: python -m pytest")
    else:
        print("❌ Some validation checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
