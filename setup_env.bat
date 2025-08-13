@echo off
REM Pocket Option Trading Bot - Environment Setup Script for Windows

echo 🚀 Setting up Pocket Option Trading Bot environment...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python is installed

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📚 Installing dependencies...
pip install -r requirements.txt

REM Install Playwright browsers
echo 🎭 Installing Playwright browsers...
playwright install

REM Create .env file if it doesn't exist
if not exist .env (
    echo ⚙️ Creating .env file from template...
    copy .env.example .env
    echo 📝 Please edit .env file with your API keys and configuration
)

REM Initialize Git repository if not already initialized
if not exist .git (
    echo 🔄 Initializing Git repository...
    git init
    git add .
    git commit -m "Initial commit: Project setup"
)

echo ✅ Environment setup complete!
echo.
echo Next steps:
echo 1. Activate the virtual environment: venv\Scripts\activate.bat
echo 2. Edit .env file with your API keys
echo 3. Run the application: streamlit run src/frontend/app.py
echo.
echo Development commands:
echo - Format code: black .
echo - Lint code: flake8 src/
echo - Run tests: pytest
echo - Type check: mypy src/

pause