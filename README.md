# Pocket Option Trading Bot

An automated trading bot for the Pocket Option platform featuring real-time signal generation, risk management, and a comprehensive Streamlit dashboard.

## Features

- 🤖 **Automated Trading**: RSI + SMA crossover strategy with 80%+ target win rate
- 📊 **Real-time Dashboard**: Streamlit-based web interface with live charts and controls
- 🔒 **Risk Management**: Demo mode, position sizing, and loss limits
- 📱 **Telegram Notifications**: Real-time alerts for trades and system status
- 🧪 **Comprehensive Testing**: 80% code coverage with unit and E2E tests
- 🔐 **Security First**: Encrypted API keys and secure configuration management

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Git (optional, for version control)

### Installation

#### Windows
```bash
# Run the setup script
setup_env.bat

# Or manual setup:
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
playwright install
copy .env.example .env
```

#### Linux/macOS
```bash
# Run the setup script
chmod +x setup_env.sh
./setup_env.sh

# Or manual setup:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
cp .env.example .env
```

### Configuration

1. Edit the `.env` file with your API credentials:
   ```env
   POCKET_OPTION_EMAIL=your_email@example.com
   POCKET_OPTION_PASSWORD=your_password
   ALPHA_VANTAGE_API_KEY=your_api_key
   TELEGRAM_BOT_TOKEN=your_bot_token
   ```

2. Start the application:
   ```bash
   streamlit run src/frontend/app.py
   ```

3. Open your browser to `http://localhost:8501`

## Project Structure

```
pocket-option-trading-bot/
├── src/
│   ├── backend/           # Core trading logic
│   ├── frontend/          # Streamlit dashboard
│   └── tests/            # Test suites
├── docs/                 # Documentation
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
└── setup_env.*          # Setup scripts
```

## Development

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 src/

# Type checking
mypy src/

# Run tests
pytest

# Test coverage
pytest --cov=src --cov-report=html
```

### Testing
```bash
# Unit tests
pytest src/tests/test_backend.py

# Frontend E2E tests
pytest src/tests/test_frontend.py

# All tests with coverage
pytest --cov=src
```

## Documentation

- [Setup Guide](docs/setup.md) - Detailed installation and configuration
- [User Guide](docs/features.md) - Dashboard usage and trading controls
- [API Documentation](docs/api.md) - Integration details and troubleshooting
- [Developer Guide](docs/development.md) - Architecture and contribution guidelines

## Security & Risk Warning

⚠️ **Important**: This bot is for educational purposes. Binary options trading involves significant financial risk. Always:
- Start in demo mode
- Never risk more than you can afford to lose
- Understand the risks before using real money
- Comply with local financial regulations

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 📖 Check the [documentation](docs/)
- 🐛 Report issues on GitHub
- 💬 Join our community discussions