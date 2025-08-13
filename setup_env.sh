#!/bin/bash

# Pocket Option Trading Bot - Environment Setup Script

echo "🚀 Setting up Pocket Option Trading Bot environment..."

# Check if Python 3.10+ is installed
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version is compatible"
else
    echo "❌ Python 3.10+ is required. Current version: $python_version"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
playwright install

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys and configuration"
fi

# Initialize Git repository if not already initialized
if [ ! -d .git ]; then
    echo "🔄 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: Project setup"
fi

echo "✅ Environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Edit .env file with your API keys"
echo "3. Run the application: streamlit run src/frontend/app.py"
echo ""
echo "Development commands:"
echo "- Format code: black ."
echo "- Lint code: flake8 src/"
echo "- Run tests: pytest"
echo "- Type check: mypy src/"